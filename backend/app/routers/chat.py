import json
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.deps import get_db, get_current_user
from app.models import User, ChatSession, ChatMessage
from app.schemas import ChatIn, ChatMessageOut, ChatReplyOut, CitationOut
from app.services import llm
from app.services import retrieval
from app.services import guardrails
from app.services import topic_guard
from app.services.nutrition_context import gather_context, render_system_prompt

router = APIRouter(prefix="/chat", tags=["chat"])

HISTORY_LIMIT = 10   # số lượt gần nhất đưa lại cho model
TOP_K = 3            # số đoạn tài liệu đưa vào ngữ cảnh (rút gọn để tăng tốc)


def _chat(messages: list[dict], user: User) -> str:
    """Chat qua AI Provider Adapter (Ollama nội bộ hoặc cloud, xem services/llm.py)."""
    return llm.chat(messages, user=user, purpose="chat", ollama_model=settings.OLLAMA_CHAT_MODEL)


def _chat_stream(messages: list[dict], user: User):
    """Chat streaming qua cùng adapter với endpoint thường."""
    return llm.chat_stream(messages, user=user, purpose="chat", ollama_model=settings.OLLAMA_CHAT_MODEL)


def _in_scope(db: Session, session: ChatSession, message: str, hits: list) -> bool:
    """Chặn câu ngoài phạm vi trước khi gọi LLM (services/topic_guard.py)."""
    in_conversation = db.query(ChatMessage.id).filter(
        ChatMessage.session_id == session.id, ChatMessage.role == "assistant",  # type: ignore
    ).first() is not None
    return topic_guard.is_in_scope(message, has_rag_hits=bool(hits), in_conversation=in_conversation)


def _get_or_create_session(db: Session, user: User) -> ChatSession:
    """Mỗi người dùng có một phiên trò chuyện cuốn chiếu duy nhất."""
    session = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == user.id)
        .order_by(ChatSession.created_at.asc())
        .first()
    )
    if session is None:
        session = ChatSession(user_id=user.id, title="Trợ lý AI")
        db.add(session)
        db.commit()
        db.refresh(session)
    return session


def _citations_by_message(db: Session, message_ids: list[int]) -> dict[int, list[CitationOut]]:
    """Nạp nguồn trích dẫn cho nhiều tin nhắn một lượt (tránh N+1)."""
    if not message_ids:
        return {}
    rows = db.execute(text("""
        SELECT mc.message_id, d.title, d.source_url, c.content
        FROM message_citations mc
        JOIN doc_chunks c ON c.id = mc.chunk_id
        JOIN documents  d ON d.id = c.document_id
        WHERE mc.message_id = ANY(:ids)
        ORDER BY mc.message_id, mc.rank
    """), {"ids": message_ids}).mappings().all()

    out: dict[int, list[CitationOut]] = {}
    for r in rows:
        snippet = (r["content"] or "").strip()
        if len(snippet) > retrieval.SNIPPET_CHARS:
            snippet = snippet[:retrieval.SNIPPET_CHARS].rstrip() + "…"
        out.setdefault(r["message_id"], []).append(
            CitationOut(title=r["title"], url=r["source_url"], snippet=snippet)
        )
    return out


@router.get("/messages", response_model=list[ChatMessageOut])
def history(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    session = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == user.id)  # type: ignore
        .order_by(ChatSession.created_at.asc())
        .first()
    )
    if session is None:
        return []

    msgs = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session.id, ChatMessage.role != "system")  # type: ignore
        .order_by(ChatMessage.id.asc())
        .all()
    )
    # Trả kèm nguồn trích dẫn để tải lại trang vẫn thấy nguồn
    cites = _citations_by_message(db, [int(m.id) for m in msgs])  # type: ignore
    return [
        ChatMessageOut(
            id=int(m.id), role=str(m.role), content=str(m.content), created_at=m.created_at,  # type: ignore
            citations=cites.get(int(m.id), []),  # type: ignore
        )
        for m in msgs
    ]


@router.post("/messages", response_model=ChatReplyOut)
def send_message(
    payload: ChatIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    session = _get_or_create_session(db, user)

    # Lưu tin nhắn người dùng NGAY (kể cả khi AI lỗi vẫn còn trong lịch sử)
    db.add(ChatMessage(session_id=session.id, role="user", content=payload.message))
    db.commit()

    # Truy hồi tri thức (RAG). Không có tài liệu liên quan → hits rỗng, vẫn trả lời
    # dựa trên hồ sơ người dùng như trước.
    ctx = gather_context(db, user)
    hits = retrieval.search_chunks(db, payload.message, k=TOP_K)

    if not _in_scope(db, session, payload.message, hits):
        db.add(ChatMessage(session_id=session.id, role="assistant", content=topic_guard.REFUSAL))
        db.commit()
        return ChatReplyOut(reply=topic_guard.REFUSAL, citations=[], warnings=[])

    rag_block = retrieval.render_context_block(hits)
    # Chỉ thị dược phẩm chỉ chèn khi câu hỏi về thuốc - nó ra lệnh ghi đè lên RAG nên
    # gắn vô điều kiện sẽ làm trợ lý từ chối trả lời câu hỏi dinh dưỡng.
    system_prompt = render_system_prompt(ctx) + rag_block

    recent = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session.id, ChatMessage.role != "system")  # type: ignore
        .order_by(ChatMessage.id.desc())
        .limit(HISTORY_LIMIT)
        .all()
    )
    recent.reverse()   # cũ -> mới

    messages = [{"role": "system", "content": system_prompt}]
    messages += [{"role": m.role, "content": m.content} for m in recent]

    try:
        reply = _chat(messages, user)
    except llm.LLMError:
        raise HTTPException(
            503, "Trợ lý AI tạm thời không phản hồi được, vui lòng thử lại sau ít phút."
        )

    answer = ChatMessage(session_id=session.id, role="assistant", content=reply)
    db.add(answer)
    db.flush()   # lấy answer.id để gắn trích dẫn

    for rank, hit in enumerate(hits, start=1):
        db.execute(text("""
            INSERT INTO message_citations (message_id, chunk_id, score, rank)
            VALUES (:mid, :cid, :score, :rank)
            ON CONFLICT DO NOTHING
        """), {"mid": answer.id, "cid": hit.chunk_id,
               "score": round(hit.score, 4), "rank": rank})

    db.commit()

    # Guardrail chạy SAU LLM: dị nguyên trong câu trả lời, thiếu trích dẫn đã duyệt
    warnings = guardrails.check_chat_reply(reply, guardrails.profile_from_user(user), len(hits))

    return ChatReplyOut(
        reply=reply,
        citations=[CitationOut(**retrieval.to_citation(h)) for h in hits],
        warnings=warnings,
    )


@router.post("/stream")
def stream_message(
    payload: ChatIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Stream token phản hồi từ AI qua Server-Sent Events (SSE)."""
    session = _get_or_create_session(db, user)

    # 1. Lưu tin nhắn người dùng
    db.add(ChatMessage(session_id=session.id, role="user", content=payload.message))
    db.commit()

    # 2. Truy hồi RAG & xây dựng System Prompt
    ctx = gather_context(db, user)
    hits = retrieval.search_chunks(db, payload.message, k=TOP_K)

    if not _in_scope(db, session, payload.message, hits):
        db.add(ChatMessage(session_id=session.id, role="assistant", content=topic_guard.REFUSAL))
        db.commit()

        def refusal_events():
            yield f"data: {json.dumps({'token': topic_guard.REFUSAL}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'done': True, 'citations': [], 'warnings': []}, ensure_ascii=False)}\n\n"
        return StreamingResponse(refusal_events(), media_type="text/event-stream")

    guard_profile = guardrails.profile_from_user(user)
    rag_block = retrieval.render_context_block(hits)
    system_prompt = render_system_prompt(ctx) + rag_block

    recent = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session.id, ChatMessage.role != "system")  # type: ignore
        .order_by(ChatMessage.id.desc())
        .limit(HISTORY_LIMIT)
        .all()
    )
    recent.reverse()

    messages = [{"role": "system", "content": system_prompt}]
    messages += [{"role": m.role, "content": m.content} for m in recent]

    def event_generator():
        full_reply = []
        try:
            for token in _chat_stream(messages, user):
                full_reply.append(token)
                yield f"data: {json.dumps({'token': token}, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"
            return

        full_text = "".join(full_reply).strip()
        if full_text:
            answer = ChatMessage(session_id=session.id, role="assistant", content=full_text)
            db.add(answer)
            db.flush()
            for rank, hit in enumerate(hits, start=1):
                db.execute(text("""
                    INSERT INTO message_citations (message_id, chunk_id, score, rank)
                    VALUES (:mid, :cid, :score, :rank)
                    ON CONFLICT DO NOTHING
                """), {"mid": answer.id, "cid": hit.chunk_id, "score": round(hit.score, 4), "rank": rank})
            db.commit()

        cites = [retrieval.to_citation(h) for h in hits]
        # Guardrail chạy SAU LLM, gửi kèm sự kiện kết thúc
        warnings = guardrails.check_chat_reply(full_text, guard_profile, len(hits))
        done = {"done": True, "citations": cites, "warnings": warnings}
        yield f"data: {json.dumps(done, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.delete("/messages", status_code=204)
def clear_history(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Xóa toàn bộ lịch sử trò chuyện của người dùng."""
    session = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == user.id)  # type: ignore
        .first()
    )
    if session:
        db.query(ChatMessage).filter(ChatMessage.session_id == session.id).delete()  # type: ignore
        db.commit()
    return None

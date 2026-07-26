from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.deps import get_db, get_current_user
from app.models import User, ChatSession, ChatMessage
from app.schemas import ChatIn, ChatMessageOut, ChatReplyOut, CitationOut
from app.services import ollama_client
from app.services import retrieval
from app.services.nutrition_context import build_system_prompt

router = APIRouter(prefix="/chat", tags=["chat"])

HISTORY_LIMIT = 10   # số lượt gần nhất đưa lại cho model
TOP_K = 5            # số đoạn tài liệu đưa vào ngữ cảnh


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
        .filter(ChatSession.user_id == user.id)
        .order_by(ChatSession.created_at.asc())
        .first()
    )
    if session is None:
        return []

    msgs = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session.id, ChatMessage.role != "system")
        .order_by(ChatMessage.id.asc())
        .all()
    )
    # Trả kèm nguồn trích dẫn để tải lại trang vẫn thấy nguồn
    cites = _citations_by_message(db, [m.id for m in msgs])
    return [
        ChatMessageOut(
            id=m.id, role=m.role, content=m.content, created_at=m.created_at,
            citations=cites.get(m.id, []),
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
    hits = retrieval.search_chunks(db, payload.message, k=TOP_K)

    system_prompt = build_system_prompt(db, user) + retrieval.render_context_block(hits)

    recent = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session.id, ChatMessage.role != "system")
        .order_by(ChatMessage.id.desc())
        .limit(HISTORY_LIMIT)
        .all()
    )
    recent.reverse()   # cũ -> mới

    messages = [{"role": "system", "content": system_prompt}]
    messages += [{"role": m.role, "content": m.content} for m in recent]

    try:
        reply = ollama_client.chat(messages)
    except ollama_client.OllamaError:
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

    return ChatReplyOut(
        reply=reply,
        citations=[CitationOut(**retrieval.to_citation(h)) for h in hits],
    )

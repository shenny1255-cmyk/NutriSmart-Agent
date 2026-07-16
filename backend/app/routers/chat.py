from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.deps import get_db, get_current_user
from app.models import User, ChatSession, ChatMessage
from app.schemas import ChatIn, ChatMessageOut, ChatReplyOut
from app.services import ollama_client
from app.services.nutrition_context import build_system_prompt

router = APIRouter(prefix="/chat", tags=["chat"])

HISTORY_LIMIT = 10   # số lượt gần nhất đưa lại cho model


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
    return (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session.id, ChatMessage.role != "system")
        .order_by(ChatMessage.id.asc())
        .all()
    )


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

    system_prompt = build_system_prompt(db, user)

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

    db.add(ChatMessage(session_id=session.id, role="assistant", content=reply))
    db.commit()

    return ChatReplyOut(reply=reply)

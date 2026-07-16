from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.deps import get_db, require_role
from app.models import User, Document, ChatMessage
from app.schemas import DocumentOut, DocumentReviewIn
from app.services.audit import write_audit

router = APIRouter(prefix="/expert", tags=["expert"])

# EXPERT hoặc ADMIN đều vào được
expert_or_admin = Depends(require_role("EXPERT", "ADMIN"))


@router.get("/documents/pending", response_model=list[DocumentOut])
def pending_documents(db: Session = Depends(get_db), _: User = expert_or_admin):
    """Tài liệu đang chờ duyệt."""
    return (
        db.query(Document)
        .filter(Document.status == "PENDING", Document.deleted_at.is_(None))
        .order_by(Document.created_at)
        .all()
    )


@router.patch("/documents/{doc_id}/review", response_model=DocumentOut)
def review_document(
    doc_id: str, payload: DocumentReviewIn,
    db: Session = Depends(get_db),
    actor: User = expert_or_admin,
):
    """Duyệt hoặc từ chối tài liệu. Duyệt xong mới đưa vào RAG (indexing)."""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(404, "Không tìm thấy tài liệu")

    before = {"status": doc.status}
    doc.status = payload.status  # type: ignore
    doc.approved_by = actor.id  # type: ignore
    doc.approved_at = datetime.now(timezone.utc)  # type: ignore

    write_audit(db, actor.id, "APPROVE", "documents", doc_id,
                before=before, after={"status": payload.status})
    db.commit()
    db.refresh(doc)

    # TODO: nếu APPROVED → đẩy vào pipeline chunk + embedding
    return doc


@router.patch("/chat-messages/{msg_id}/flag")
def flag_message(
    msg_id: int,
    db: Session = Depends(get_db),
    actor: User = expert_or_admin,
):
    """Gắn cờ câu trả lời AI sai lệch (kiểm định tri thức)."""
    msg = db.query(ChatMessage).filter(ChatMessage.id == msg_id).first()
    if not msg:
        raise HTTPException(404, "Không tìm thấy tin nhắn")

    msg.flagged = True  # type: ignore
    write_audit(db, actor.id, "UPDATE", "chat_messages", str(msg_id),
                after={"flagged": True})
    db.commit()
    return {"message": "Đã gắn cờ câu trả lời sai lệch"}
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.deps import get_db, require_role
from app.models import User, Document, ChatMessage, DocChunk
from app.schemas import DocumentOut, DocumentReviewIn, CrawlIn, CrawlOut, CrawlPresetIn
from app.services.audit import write_audit
from app.services.indexer import run_indexing_pipeline
from app.services.scraper import crawl_urls, crawl_preset_sources

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
    background_tasks: BackgroundTasks,
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

    if payload.status == "APPROVED":
        background_tasks.add_task(run_indexing_pipeline, str(doc.id))

    return doc


@router.post("/documents/crawl", response_model=CrawlOut)
def crawl_documents(
    payload: CrawlIn,
    db: Session = Depends(get_db),
    actor: User = expert_or_admin,
):
    """Cào bài viết y khoa từ danh sách URL và lưu vào DB ở trạng thái PENDING."""
    return crawl_urls(payload.urls, db, uploaded_by_id=actor.id)


@router.post("/documents/crawl-preset", response_model=CrawlOut)
def crawl_preset_documents(
    payload: CrawlPresetIn,
    db: Session = Depends(get_db),
    actor: User = expert_or_admin,
):
    """Cào tự động N bài viết y khoa từ nguồn uy tín chọn sẵn (Bộ Y tế 'moh', WHO 'who', hoặc 'all')."""
    return crawl_preset_sources(source_key=payload.source, limit=payload.limit, db=db, uploaded_by_id=actor.id)


@router.post("/documents/reset")
def reset_documents(
    db: Session = Depends(get_db),
    actor: User = expert_or_admin,
):
    """Xóa tất cả tài liệu và doc_chunks để phục vụ demo/test lại từ đầu."""
    db.query(DocChunk).delete()
    db.query(Document).delete()
    write_audit(db, actor.id, "DELETE", "documents", "ALL_RESET")
    db.commit()
    return {"message": "Đã reset sạch danh sách tài liệu để sẵn sàng demo lại từ đầu."}





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
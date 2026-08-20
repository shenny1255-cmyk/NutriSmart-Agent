from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.deps import get_db, require_role
from app.models import User, Document, ChatMessage, DocChunk, CrawlSource
from app.schemas import (
    DocumentOut, DocumentReviewIn, CrawlIn, CrawlOut, CrawlPresetIn,
    DocPreviewOut, CrawlSourceOut, CrawlSourceCreateIn,
)
from app.services.audit import write_audit
from app.services.doc_upload import (
    doc_text_tu_file, LoaiFileKhongHoTro, DUOI_FILE_HO_TRO, KICH_THUOC_TOI_DA,
)
from app.services.indexer import run_indexing_pipeline, split_text
from app.services.scraper import crawl_urls, crawl_preset_sources

DO_DAI_NOI_DUNG_TOI_THIEU = 100

router = APIRouter(prefix="/expert", tags=["expert"])

expert_or_admin = Depends(require_role("EXPERT", "ADMIN"))


@router.get("/documents/pending", response_model=list[DocumentOut])
def pending_documents(db: Session = Depends(get_db), _: User = expert_or_admin):
    """Tài liệu đang chờ duyệt."""
    return (
        db.query(Document)
        .filter(Document.status == "PENDING", Document.deleted_at.is_(None))  # type: ignore
        .order_by(Document.created_at)
        .all()
    )


@router.get("/documents/{doc_id}/preview", response_model=DocPreviewOut)
def preview_document(
    doc_id: str,
    db: Session = Depends(get_db),
    _: User = expert_or_admin,
):
    """Xem trước tiêu đề, nội dung bóc tách và các đoạn chunks dự kiến sẽ được index RAG."""
    doc = db.query(Document).filter(Document.id == doc_id, Document.deleted_at.is_(None)).first()  # type: ignore
    if not doc:
        raise HTTPException(404, "Không tìm thấy tài liệu")

    chunks = split_text(doc.raw_text or "", title=doc.title, source_name=doc.source_name)
    estimated_chunks = [
        {"chunk_index": i, "content": c, "token_count": len(c.split())}
        for i, c in enumerate(chunks)
    ]

    return {
        "id": doc.id,
        "title": doc.title,
        "source_name": doc.source_name,
        "source_url": doc.source_url,
        "status": doc.status,
        "raw_text": doc.raw_text or "",
        "estimated_chunks": estimated_chunks,
    }


@router.patch("/documents/{doc_id}/review", response_model=DocumentOut)
def review_document(
    doc_id: str, payload: DocumentReviewIn,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    actor: User = expert_or_admin,
):
    """Duyệt hoặc từ chối tài liệu. Duyệt xong mới đưa vào RAG (indexing)."""
    doc = db.query(Document).filter(Document.id == doc_id).first()  # type: ignore
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


@router.get("/crawl-sources", response_model=list[CrawlSourceOut])
def list_crawl_sources(
    db: Session = Depends(get_db),
    _: User = expert_or_admin,
):
    """Lấy danh sách các nguồn cào tự động động."""
    try:
        sources = db.query(CrawlSource).filter(CrawlSource.is_active == True).order_by(CrawlSource.created_at).all()  # type: ignore
        return sources
    except Exception:
        return []


@router.post("/crawl-sources", response_model=CrawlSourceOut, status_code=201)
def create_crawl_source(
    payload: CrawlSourceCreateIn,
    db: Session = Depends(get_db),
    actor: User = expert_or_admin,
):
    """Thêm nguồn cào dữ liệu y khoa mới."""
    existing = db.query(CrawlSource).filter(CrawlSource.source_key == payload.source_key).first()  # type: ignore
    if existing:
        raise HTTPException(400, f"Mã nguồn '{payload.source_key}' đã tồn tại.")

    source = CrawlSource(
        name=payload.name,
        source_key=payload.source_key,
        domain=payload.domain,
        base_urls=payload.base_urls,
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    write_audit(db, actor.id, "CREATE", "crawl_sources", str(source.id), after={"name": source.name})
    return source


@router.delete("/crawl-sources/{source_id}")
def delete_crawl_source(
    source_id: str,
    db: Session = Depends(get_db),
    actor: User = expert_or_admin,
):
    """Xóa / ẩn nguồn cào."""
    source = db.query(CrawlSource).filter(CrawlSource.id == source_id).first()  # type: ignore
    if not source:
        raise HTTPException(404, "Không tìm thấy nguồn cào")

    source.is_active = False
    db.commit()
    write_audit(db, actor.id, "DELETE", "crawl_sources", source_id)
    return {"message": "Đã ẩn nguồn cào thành công."}


def luu_tai_lieu_upload(
    db: Session, actor: User, title: str, raw_text: str,
    category_id: int | None = None, source_name: str | None = None,
) -> Document:
    """Tạo tài liệu PENDING từ nội dung tải lên. Vẫn phải qua duyệt mới vào RAG."""
    noi_dung = (raw_text or "").strip()
    if len(noi_dung) < DO_DAI_NOI_DUNG_TOI_THIEU:
        raise HTTPException(
            400,
            f"Nội dung quá ngắn ({len(noi_dung)} ký tự). Tài liệu cần ít nhất "
            f"{DO_DAI_NOI_DUNG_TOI_THIEU} ký tự để chia đoạn cho RAG. "
            "Nếu là PDF ảnh scan thì phải OCR trước."
        )

    doc = Document(
        title=(title or "").strip() or "Tài liệu không tiêu đề",
        category_id=category_id,
        source_name=source_name or "Tải lên thủ công",
        raw_text=noi_dung,
        status="PENDING",
        uploaded_by=actor.id,
    )
    db.add(doc)
    db.flush()
    write_audit(db, actor.id, "CREATE", "documents", str(doc.id),
                after={"title": doc.title, "source_name": doc.source_name})
    db.commit()
    db.refresh(doc)
    return doc


@router.post("/documents/upload", response_model=DocumentOut, status_code=201)
async def upload_document(
    title: str = Form(...),
    category_id: int | None = Form(None),
    raw_text: str | None = Form(None),
    file: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    actor: User = expert_or_admin,
):
    """Tải tài liệu lên: chọn file (.txt/.md/.pdf) hoặc dán thẳng nội dung."""
    noi_dung = (raw_text or "").strip()
    nguon = "Tải lên thủ công"

    if file and file.filename:
        du_lieu = await file.read()
        if len(du_lieu) > KICH_THUOC_TOI_DA:
            raise HTTPException(
                413, f"File vượt quá {KICH_THUOC_TOI_DA // (1024 * 1024)} MB."
            )
        try:
            noi_dung = doc_text_tu_file(file.filename, du_lieu)
        except LoaiFileKhongHoTro as e:
            raise HTTPException(400, str(e))
        nguon = file.filename

    if not noi_dung:
        raise HTTPException(400, f"Cần chọn file ({', '.join(DUOI_FILE_HO_TRO)}) hoặc dán nội dung tài liệu.")

    return luu_tai_lieu_upload(db, actor, title, noi_dung, category_id, nguon)


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
    msg = db.query(ChatMessage).filter(ChatMessage.id == msg_id).first()  # type: ignore
    if not msg:
        raise HTTPException(404, "Không tìm thấy tin nhắn")

    msg.flagged = True  # type: ignore
    write_audit(db, actor.id, "UPDATE", "chat_messages", str(msg_id),
                after={"flagged": True})
    db.commit()
    return {"message": "Đã gắn cờ câu trả lời sai lệch"}

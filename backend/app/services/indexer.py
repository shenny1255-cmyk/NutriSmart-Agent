"""Dịch vụ cắt nhỏ văn bản (Chunking) và tạo ma trận số (Embedding) lưu vào DB.

Khi Chuyên gia duyệt (APPROVE) một tài liệu, luồng này sẽ được gọi bất đồng bộ.
"""

import logging
from app.database import SessionLocal
from app.models import Document, DocChunk
from app.services.ollama_client import get_embedding, OllamaError

logger = logging.getLogger(__name__)


def split_text(text: str, chunk_size: int = 500, chunk_overlap: int = 100) -> list[str]:
    """Cắt văn bản thô thành danh sách các đoạn (chunks) nhỏ hơn.
    
    Cố gắng tìm khoảng trắng gần nhất để không cắt ngang từ.
    """
    if not text:
        return []
    
    chunks = []
    start = 0
    text_len = len(text)
    
    while start < text_len:
        end = min(start + chunk_size, text_len)
        
        # Nếu chưa tới cuối văn bản, lùi lại tìm khoảng trắng thích hợp
        if end < text_len:
            last_space = text.rfind(" ", start, end)
            if last_space != -1 and last_space > start + (chunk_size // 2):
                end = last_space
                
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
            
        if end >= text_len:
            break
            
        # Dịch chuyển vị trí bắt đầu cho chunk tiếp theo có tính đến overlap
        start = max(start + 1, end - chunk_overlap)
        
    return chunks


def run_indexing_pipeline(doc_id: str):
    """Pipeline chính: Tải tài liệu, cắt chunk, sinh vector embedding và lưu DB.
    
    Hàm này chạy độc lập dưới dạng Background Task với SessionLocal riêng.
    """
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if not doc:
            logger.error(f"[RAG Indexer] Không tìm thấy tài liệu {doc_id}")
            return

        if not doc.raw_text or not doc.raw_text.strip():
            logger.warning(f"[RAG Indexer] Tài liệu {doc_id} ('{doc.title}') có raw_text rỗng, bỏ qua chunking.")
            return

        # Xóa các chunk cũ của tài liệu này để đảm bảo tính Idempotent (không bị trùng lặp khi duyệt lại)
        db.query(DocChunk).filter(DocChunk.document_id == doc.id).delete()
        db.flush()

        text_chunks = split_text(doc.raw_text)
        logger.info(f"[RAG Indexer] Đã cắt tài liệu {doc_id} thành {len(text_chunks)} chunks.")

        chunks_to_insert = []
        for idx, chunk_content in enumerate(text_chunks):
            vector = None
            try:
                vector = get_embedding(chunk_content)
            except OllamaError as e:
                logger.error(f"[RAG Indexer] Lỗi khi tạo embedding cho chunk {idx} của tài liệu {doc_id}: {e}")

            token_count = len(chunk_content.split())
            chunks_to_insert.append(
                DocChunk(
                    document_id=doc.id,
                    chunk_index=idx,
                    content=chunk_content,
                    token_count=token_count,
                    embedding=vector,
                )
            )

        db.add_all(chunks_to_insert)
        db.commit()
        logger.info(f"[RAG Indexer] Hoàn tất index thành công tài liệu {doc_id} với {len(chunks_to_insert)} chunks.")

    except Exception as e:
        db.rollback()
        logger.error(f"[RAG Indexer] Thất bại khi chạy pipeline index cho tài liệu {doc_id}: {e}", exc_info=True)
    finally:
        db.close()

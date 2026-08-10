"""Dịch vụ cắt nhỏ văn bản ngữ nghĩa (Semantic Chunking) và tạo vector embedding cho RAG.

Khi Chuyên gia duyệt (APPROVE) một tài liệu, luồng này sẽ được gọi bất đồng bộ.
"""

import logging
import re
import threading

from app.database import SessionLocal
from app.models import Document, DocChunk
from app.services.ollama_client import get_embedding, OllamaError

logger = logging.getLogger(__name__)

_khoa_index = threading.Lock()
EMBEDDING_TIMEOUT_SECONDS = 300.0


def split_text(
    text: str,
    chunk_size: int = 800,
    chunk_overlap: int = 100,
    title: str | None = None,
    source_name: str | None = None,
) -> list[str]:
    """Cắt văn bản thô thành danh sách các đoạn (chunks) dựa trên phân đoạn ngữ nghĩa (Semantic Chunking).

    Ưu tiên chia theo đoạn văn (\\n\\n), tiêu đề (H2, H3) và câu thay vì cắt từ thô ở giữa câu.
    Bổ sung tiêu đề & nguồn tài liệu vào đầu mỗi chunk nếu có.
    """
    if not text or not text.strip():
        return []

    context_header = ""
    if title:
        source_str = f" | Nguồn: {source_name}" if source_name else ""
        context_header = f"[Tài liệu: {title}{source_str}]\n\n"

    # Tách đoạn văn dựa trên dải xuống dòng kép hoặc tiêu đề markdown (##, ###)
    raw_paragraphs = re.split(r"(\n\s*\n|(?=^#{1,3}\s+))", text, flags=re.MULTILINE)
    paragraphs = [p.strip() for p in raw_paragraphs if p and p.strip()]

    if not paragraphs:
        tokens = text.split()
        if not tokens:
            return []
        chunks = [" ".join(tokens[i:i + chunk_size]) for i in range(0, len(tokens), chunk_size - chunk_overlap)]
        return [f"{context_header}{c}" if context_header else c for c in chunks]

    chunks = []
    current_tokens = []
    current_count = 0

    for p in paragraphs:
        p_tokens = p.split()
        p_len = len(p_tokens)

        # Nếu 1 paragraph quá dài, cắt nhỏ theo câu hoặc theo từ
        if p_len > chunk_size:
            if current_tokens:
                chunk_str = " ".join(current_tokens)
                chunks.append(f"{context_header}{chunk_str}" if context_header else chunk_str)
                current_tokens = []
                current_count = 0

            # Cắt p thành các câu
            sentences = re.split(r"(?<=[.!?])\s+", p)
            s_tokens_acc = []
            s_count = 0
            for s in sentences:
                st = s.split()
                if s_count + len(st) <= chunk_size:
                    s_tokens_acc.extend(st)
                    s_count += len(st)
                else:
                    if s_tokens_acc:
                        chunk_str = " ".join(s_tokens_acc)
                        chunks.append(f"{context_header}{chunk_str}" if context_header else chunk_str)
                    s_tokens_acc = st
                    s_count = len(st)
            if s_tokens_acc:
                chunk_str = " ".join(s_tokens_acc)
                chunks.append(f"{context_header}{chunk_str}" if context_header else chunk_str)
            continue

        if current_count + p_len <= chunk_size:
            current_tokens.extend(p_tokens)
            current_count += p_len
        else:
            chunk_str = " ".join(current_tokens)
            chunks.append(f"{context_header}{chunk_str}" if context_header else chunk_str)
            
            # Xử lý overlap: giữ lại 1 phần token cuối làm overlap
            overlap_tokens = current_tokens[-chunk_overlap:] if chunk_overlap < current_count else []
            current_tokens = overlap_tokens + p_tokens
            current_count = len(current_tokens)

    if current_tokens:
        chunk_str = " ".join(current_tokens)
        chunks.append(f"{context_header}{chunk_str}" if context_header else chunk_str)

    return chunks


def run_indexing_pipeline(doc_id: str):
    """Pipeline chính: Tải tài liệu, cắt chunk ngữ nghĩa, sinh vector embedding và lưu DB."""
    with _khoa_index:
        _index_mot_tai_lieu(doc_id)


def _index_mot_tai_lieu(doc_id: str):
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == doc_id).first()  # type: ignore
        if not doc:
            logger.error(f"[RAG Indexer] Không tìm thấy tài liệu {doc_id}")
            return

        if not doc.raw_text or not doc.raw_text.strip():
            logger.warning(f"[RAG Indexer] Tài liệu {doc_id} ('{doc.title}') có raw_text rỗng, bỏ qua chunking.")
            return

        db.query(DocChunk).filter(DocChunk.document_id == doc.id).delete()  # type: ignore
        db.flush()

        text_chunks = split_text(doc.raw_text, title=doc.title, source_name=doc.source_name)
        logger.info(f"[RAG Indexer] Đã cắt tài liệu {doc_id} thành {len(text_chunks)} semantic chunks.")

        chunks_to_insert = []
        for idx, chunk_content in enumerate(text_chunks):
            vector = None
            try:
                vector = get_embedding(chunk_content, timeout=EMBEDDING_TIMEOUT_SECONDS)
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

        thieu_vector = sum(1 for c in chunks_to_insert if c.embedding is None)
        if thieu_vector:
            logger.error(
                f"[RAG Indexer] Tài liệu {doc_id} có {thieu_vector}/{len(chunks_to_insert)} "
                "chunk KHÔNG có embedding (Ollama lỗi). Hãy kiểm tra Ollama rồi duyệt lại tài liệu."
            )
        else:
            logger.info(f"[RAG Indexer] Hoàn tất index thành công tài liệu {doc_id} với {len(chunks_to_insert)} chunks.")

    except Exception as e:
        db.rollback()
        logger.error(f"[RAG Indexer] Thất bại khi chạy pipeline index cho tài liệu {doc_id}: {e}", exc_info=True)
    finally:
        db.close()

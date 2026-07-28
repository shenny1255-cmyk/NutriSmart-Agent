"""Integration: hybrid search thật trên Postgres + embedding thật (bge-m3).

Bỏ qua nếu thiếu Postgres hoặc Ollama — CI/máy khác vẫn chạy được phần còn lại.
"""

import uuid

import pytest
from sqlalchemy import text

from app.database import engine, SessionLocal
from app.services.retrieval import search_chunks, MIN_SCORE
from app.services.ollama_client import get_embedding, OllamaError


def _db_up() -> bool:
    try:
        with engine.connect() as c:
            c.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def _ollama_up() -> bool:
    try:
        get_embedding("ping")
        return True
    except (OllamaError, Exception):
        return False


pytestmark = pytest.mark.skipif(
    not (_db_up() and _ollama_up()), reason="Cần Postgres và Ollama (bge-m3) để chạy"
)

DOC_TEXT = (
    "Người bị bệnh gout nên hạn chế thực phẩm giàu purin như nội tạng động vật, "
    "hải sản và bia rượu. Nên uống nhiều nước và ăn nhiều rau xanh."
)


@pytest.fixture
def indexed_doc():
    """Tạo 1 tài liệu APPROVED + 1 chunk có embedding thật, dọn sạch sau khi test."""
    db = SessionLocal()
    doc_id = uuid.uuid4()
    db.execute(text("""
        INSERT INTO documents (id, title, source_url, source_name, raw_text, status)
        VALUES (:id, :t, :u, :s, :raw, 'APPROVED')
    """), {"id": str(doc_id), "t": "Chế độ ăn cho người bệnh gout",
           "u": "https://example.test/gout", "s": "test", "raw": DOC_TEXT})
    db.execute(text("""
        INSERT INTO doc_chunks (document_id, chunk_index, content, token_count, embedding)
        VALUES (:d, 0, :c, :n, CAST(:e AS vector))
    """), {"d": str(doc_id), "c": DOC_TEXT, "n": len(DOC_TEXT.split()),
           "e": str(get_embedding(DOC_TEXT))})
    db.commit()
    yield db, doc_id
    db.execute(text("DELETE FROM documents WHERE id = :id"), {"id": str(doc_id)})
    db.commit()
    db.close()


def test_finds_relevant_chunk_with_citation_fields(indexed_doc):
    db, doc_id = indexed_doc
    hits = search_chunks(db, "Bệnh gout kiêng ăn gì?")

    assert hits, "phải tìm được tài liệu về gout"
    top = hits[0]
    assert "gout" in top.doc_title.lower()
    assert top.score >= MIN_SCORE
    assert top.source_url == "https://example.test/gout"   # UI cần link nguồn


def test_offtopic_question_returns_no_hits(indexed_doc):
    db, _ = indexed_doc
    # Câu lạc đề → không trích dẫn bừa (ngưỡng MIN_SCORE lọc sạch)
    assert search_chunks(db, "Hôm nay mấy giờ rồi?") == []


def test_only_approved_documents_are_searchable(indexed_doc):
    """Tài liệu chưa duyệt phải biến mất khỏi kết quả (kho có thể còn tài liệu khác).

    Bám theo chunk_id của đúng tài liệu này chứ không lọc theo chữ "gout" trong tiêu đề:
    kho tri thức thật cũng có bài về gout đã duyệt, lọc theo tiêu đề sẽ báo sai.
    """
    db, doc_id = indexed_doc
    q = "Bệnh gout kiêng ăn gì?"
    chunk_cua_tai_lieu = {
        r[0] for r in db.execute(
            text("SELECT id FROM doc_chunks WHERE document_id = :id"), {"id": str(doc_id)}
        )
    }
    assert chunk_cua_tai_lieu, "Fixture phải tạo được ít nhất 1 chunk"
    assert any(h.chunk_id in chunk_cua_tai_lieu for h in search_chunks(db, q))

    db.execute(text("UPDATE documents SET status='PENDING' WHERE id=:id"), {"id": str(doc_id)})
    db.commit()
    assert not any(h.chunk_id in chunk_cua_tai_lieu for h in search_chunks(db, q))

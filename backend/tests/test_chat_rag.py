"""Router: /chat/messages trả kèm nguồn trích dẫn và ghi message_citations.

Retrieval + LLM đều được monkeypatch → không cần Ollama, chỉ cần Postgres.
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.main import app
from app.database import engine, SessionLocal
import app.routers.chat as chat_router
from app.services import ollama_client
from app.services.retrieval import Hit


def _db_up() -> bool:
    try:
        with engine.connect() as c:
            c.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _db_up(), reason="Postgres chưa chạy")

client = TestClient(app)


@pytest.fixture
def auth_headers(user_test):
    countries = client.get("/api/v1/catalog/countries").json()
    cc = countries[0]["code"] if countries else "VN"
    email = f"rag_{uuid.uuid4().hex[:10]}@example.com"
    r = client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "password123", "full_name": "RAG Test", "country_code": cc,
        "profile": {"gender": "MALE", "birth_date": "1996-01-01", "height_cm": 175,
                    "weight_kg": 72, "activity_level": 3, "goal": "MAINTAIN",
                    "condition_ids": [], "allergen_ids": []},
    })
    assert r.status_code == 201, r.text
    user_test.append(email)
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def real_chunk():
    """Một chunk thật trong DB để gắn message_citations (FK bắt buộc)."""
    db = SessionLocal()
    doc_id = uuid.uuid4()
    db.execute(text("""
        INSERT INTO documents (id, title, source_url, raw_text, status)
        VALUES (:id, :t, :u, 'noi dung', 'APPROVED')
    """), {"id": str(doc_id), "t": "Tài liệu kiểm thử RAG", "u": "https://example.test/rag"})
    cid = db.execute(text("""
        INSERT INTO doc_chunks (document_id, chunk_index, content)
        VALUES (:d, 0, :c) RETURNING id
    """), {"d": str(doc_id), "c": "Rau xanh giàu chất xơ tốt cho tiêu hoá."}).scalar()
    db.commit()
    yield cid
    db.execute(text("DELETE FROM documents WHERE id = :id"), {"id": str(doc_id)})
    db.commit()
    db.close()


def test_reply_carries_citations_and_persists_them(monkeypatch, auth_headers, real_chunk):
    hit = Hit(chunk_id=real_chunk, content="Rau xanh giàu chất xơ tốt cho tiêu hoá.",
              score=0.87, doc_title="Tài liệu kiểm thử RAG", source_url="https://example.test/rag")
    monkeypatch.setattr(chat_router.retrieval, "search_chunks", lambda db, q, k=5: [hit])
    monkeypatch.setattr(ollama_client, "chat", lambda messages, **kw: "Câu trả lời có nguồn.")

    r = client.post("/api/v1/chat/messages", json={"message": "Rau xanh có tốt không?"},
                    headers=auth_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["reply"] == "Câu trả lời có nguồn."
    assert len(body["citations"]) == 1
    assert body["citations"][0]["title"] == "Tài liệu kiểm thử RAG"
    assert body["citations"][0]["url"] == "https://example.test/rag"

    # Nguồn phải còn sau khi tải lại lịch sử
    hist = client.get("/api/v1/chat/messages", headers=auth_headers).json()
    assistant = [m for m in hist if m["role"] == "assistant"][-1]
    assert assistant["citations"][0]["title"] == "Tài liệu kiểm thử RAG"


def test_retrieved_context_reaches_the_prompt(monkeypatch, auth_headers, real_chunk):
    """Đoạn tài liệu tìm được phải nằm trong system prompt gửi cho LLM."""
    hit = Hit(chunk_id=real_chunk, content="Rau xanh giàu chất xơ tốt cho tiêu hoá.",
              score=0.87, doc_title="Tài liệu kiểm thử RAG", source_url=None)
    monkeypatch.setattr(chat_router.retrieval, "search_chunks", lambda db, q, k=5: [hit])

    seen = {}
    monkeypatch.setattr(ollama_client, "chat",
                        lambda messages, **kw: seen.setdefault("sys", messages[0]["content"]) and "ok" or "ok")

    client.post("/api/v1/chat/messages", json={"message": "Rau xanh?"}, headers=auth_headers)
    assert "Rau xanh giàu chất xơ" in seen["sys"]
    assert "[1]" in seen["sys"]


def test_no_hits_means_no_citations(monkeypatch, auth_headers):
    """Không có tài liệu liên quan → vẫn trả lời, chỉ là không có trích dẫn."""
    monkeypatch.setattr(chat_router.retrieval, "search_chunks", lambda db, q, k=5: [])
    monkeypatch.setattr(ollama_client, "chat", lambda messages, **kw: "Trả lời theo hồ sơ.")

    r = client.post("/api/v1/chat/messages", json={"message": "Tối nay ăn gì?"},
                    headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["citations"] == []

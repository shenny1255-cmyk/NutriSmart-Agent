"""Integration test cho /chat/messages.

Cần Postgres đang chạy (docker compose up -d). Nếu chưa có DB, cả file được skip.
ollama_client.chat được monkeypatch nên KHÔNG gọi model thật.
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.main import app
from app.database import engine
from app.services import ollama_client


def _db_up() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _db_up(), reason="Postgres chưa chạy — bỏ qua (docker compose up -d để chạy)"
)

client = TestClient(app)


def _register(user_test) -> str:
    """Đăng ký user mới, trả về access token."""
    country_code = "VN"

    email = f"chat_{uuid.uuid4().hex[:10]}@example.com"
    payload = {
        "email": email,
        "password": "password123",
        "full_name": "Người Dùng Thử",
        "country_code": country_code,
        "profile": {
            "gender": "MALE", "birth_date": "1996-01-01",
            "height_cm": 175, "weight_kg": 82, "activity_level": 3,
            "goal": "LOSE_WEIGHT", "condition_ids": [], "allergen_ids": [],
        },
    }
    r = client.post("/api/v1/auth/register", json=payload)
    assert r.status_code == 201, r.text
    user_test.append(email)
    return r.json()["access_token"]


def test_send_message_persists_user_and_assistant(monkeypatch, user_test):
    monkeypatch.setattr(ollama_client, "chat",
                        lambda messages, **kw: "Câu trả lời thử nghiệm")
    headers = {"Authorization": f"Bearer {_register(user_test)}"}

    r = client.post("/api/v1/chat/messages",
                    json={"message": "Xin chào trợ lý"}, headers=headers)
    assert r.status_code == 200, r.text
    assert r.json()["reply"] == "Câu trả lời thử nghiệm"

    history = client.get("/api/v1/chat/messages", headers=headers).json()
    assert [m["role"] for m in history] == ["user", "assistant"]
    assert history[0]["content"] == "Xin chào trợ lý"


def test_ollama_failure_returns_503_but_keeps_user_message(monkeypatch, user_test):
    def boom(messages, **kw):
        raise ollama_client.OllamaError("server down")

    monkeypatch.setattr(ollama_client, "chat", boom)
    headers = {"Authorization": f"Bearer {_register(user_test)}"}

    r = client.post("/api/v1/chat/messages",
                    json={"message": "Tin nhắn khi AI lỗi"}, headers=headers)
    assert r.status_code == 503

    history = client.get("/api/v1/chat/messages", headers=headers).json()
    assert [m["role"] for m in history] == ["user"]
    assert history[0]["content"] == "Tin nhắn khi AI lỗi"


def test_reply_kem_canh_bao_guardrail(monkeypatch, user_test):
    # Không có trích dẫn RAG → Warning Engine gắn cảnh báo NO_GROUNDING
    from app.services import retrieval
    monkeypatch.setattr(ollama_client, "chat", lambda messages, **kw: "Uống đủ nước nhé.")
    monkeypatch.setattr(retrieval, "search_chunks", lambda db, q, k=5: [])
    headers = {"Authorization": f"Bearer {_register(user_test)}"}

    r = client.post("/api/v1/chat/messages", json={"message": "Nên uống bao nhiêu nước?"},
                    headers=headers)
    assert r.status_code == 200, r.text
    assert [w["code"] for w in r.json()["warnings"]] == ["NO_GROUNDING"]


def test_stream_gui_canh_bao_di_ung_trong_su_kien_done(monkeypatch, user_test):
    # Stream: guardrail chạy trên toàn bộ câu trả lời rồi gửi kèm sự kiện `done`
    import json
    from app.services import retrieval
    monkeypatch.setattr(ollama_client, "chat_stream",
                        lambda messages, **kw: iter(["Bạn thử ", "gỏi cuốn chấm ", "tương đậu phộng nhé."]))
    monkeypatch.setattr(retrieval, "search_chunks", lambda db, q, k=5: [])
    email = f"chat_{uuid.uuid4().hex[:10]}@example.com"
    r = client.post("/api/v1/auth/register", json={
        "email": email, "password": "password123", "full_name": "Người Dùng Thử",
        "country_code": "VN",
        "profile": {
            "gender": "FEMALE", "birth_date": "1998-01-01",
            "height_cm": 160, "weight_kg": 55, "activity_level": 3,
            "goal": "MAINTAIN", "condition_ids": [], "allergen_ids": [],
            "custom_allergens": [{"name": "Đậu phộng", "severity": "SEVERE"}],
        },
    })
    assert r.status_code == 201, r.text
    user_test.append(email)
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

    r = client.post("/api/v1/chat/stream", json={"message": "Gợi ý món ăn nhẹ"}, headers=headers)
    assert r.status_code == 200, r.text
    events = [json.loads(line[len("data: "):]) for line in r.text.splitlines() if line.startswith("data: ")]
    done = next(e for e in events if e.get("done"))
    codes = [w["code"] for w in done["warnings"]]
    assert "ALLERGEN" in codes
    assert "NO_GROUNDING" in codes

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


def _register() -> str:
    """Đăng ký user mới, trả về access token."""
    countries = client.get("/api/v1/catalog/countries").json()
    country_code = countries[0]["code"] if countries else "VN"

    payload = {
        "email": f"chat_{uuid.uuid4().hex[:10]}@example.com",
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
    return r.json()["access_token"]


def test_send_message_persists_user_and_assistant(monkeypatch):
    monkeypatch.setattr(ollama_client, "chat",
                        lambda messages, **kw: "Câu trả lời thử nghiệm")
    headers = {"Authorization": f"Bearer {_register()}"}

    r = client.post("/api/v1/chat/messages",
                    json={"message": "Xin chào trợ lý"}, headers=headers)
    assert r.status_code == 200, r.text
    assert r.json()["reply"] == "Câu trả lời thử nghiệm"

    history = client.get("/api/v1/chat/messages", headers=headers).json()
    assert [m["role"] for m in history] == ["user", "assistant"]
    assert history[0]["content"] == "Xin chào trợ lý"


def test_ollama_failure_returns_503_but_keeps_user_message(monkeypatch):
    def boom(messages, **kw):
        raise ollama_client.OllamaError("server down")

    monkeypatch.setattr(ollama_client, "chat", boom)
    headers = {"Authorization": f"Bearer {_register()}"}

    r = client.post("/api/v1/chat/messages",
                    json={"message": "Tin nhắn khi AI lỗi"}, headers=headers)
    assert r.status_code == 503

    history = client.get("/api/v1/chat/messages", headers=headers).json()
    assert [m["role"] for m in history] == ["user"]
    assert history[0]["content"] == "Tin nhắn khi AI lỗi"

"""Integration: register (gửi link) → chưa xác minh → /auth/verify → đã xác minh.

Cần Postgres đang chạy. send_verification_email được monkeypatch → không gửi mail thật.
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.main import app
from app.database import engine
import app.routers.auth as auth_module


def _db_up() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _db_up(), reason="Postgres chưa chạy")

client = TestClient(app)


def _register(monkeypatch, user_test):
    captured = {}
    monkeypatch.setattr(
        auth_module, "send_verification_email",
        lambda to, link: captured.update(to=to, link=link),
    )
    countries = client.get("/api/v1/catalog/countries").json()
    cc = countries[0]["code"] if countries else "VN"
    email = f"verify_{uuid.uuid4().hex[:10]}@example.com"
    payload = {
        "email": email, "password": "password123", "full_name": "Xác Minh",
        "country_code": cc,
        "profile": {
            "gender": "MALE", "birth_date": "1996-01-01",
            "height_cm": 175, "weight_kg": 72, "activity_level": 3,
            "goal": "MAINTAIN", "condition_ids": [], "allergen_ids": [],
        },
    }
    r = client.post("/api/v1/auth/register", json=payload)
    assert r.status_code == 201, r.text
    user_test.append(email)
    return r.json()["access_token"], captured, email


def test_register_sends_link_and_user_starts_unverified(monkeypatch, user_test):
    token, captured, email = _register(monkeypatch, user_test)
    headers = {"Authorization": f"Bearer {token}"}
    me = client.get("/api/v1/auth/me", headers=headers).json()
    assert me["email_verified"] is False
    assert "/verify?token=" in captured["link"]
    assert captured["to"] == email


def test_verify_marks_user_verified(monkeypatch, user_test):
    token, captured, _ = _register(monkeypatch, user_test)
    headers = {"Authorization": f"Bearer {token}"}
    verify_token = captured["link"].split("token=")[1]

    r = client.get(f"/api/v1/auth/verify?token={verify_token}")
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "verified"

    me = client.get("/api/v1/auth/me", headers=headers).json()
    assert me["email_verified"] is True


def test_verify_bad_token_returns_400():
    r = client.get("/api/v1/auth/verify?token=not-a-real-token")
    assert r.status_code == 400


def test_resend_when_already_verified(monkeypatch, user_test):
    token, captured, _ = _register(monkeypatch, user_test)
    headers = {"Authorization": f"Bearer {token}"}
    verify_token = captured["link"].split("token=")[1]
    client.get(f"/api/v1/auth/verify?token={verify_token}")

    r = client.post("/api/v1/auth/resend-verification", headers=headers)
    assert r.status_code == 200
    assert r.json()["status"] == "already_verified"

"""Xác minh email: email được xác thực bằng mã PIN TRƯỚC khi đăng ký nên đăng ký không gửi thêm link.

Endpoint /auth/verify vẫn giữ để link đã gửi cho tài khoản cũ còn bấm được. Cần Postgres đang chạy.
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

import app.services.email as email_service
from app.main import app
from app.database import engine
from app.security import create_pin_verified_token, create_verification_token, decode_token


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
    sent = []
    monkeypatch.setattr(email_service, "send_verification_email", lambda to, link: sent.append((to, link)))
    email = f"verify_{uuid.uuid4().hex[:10]}@example.com"
    payload = {
        "email": email, "password": "Nutri#Smart2026", "full_name": "Xác Minh",
        "pin_token": create_pin_verified_token(email),
        "consents": {"terms": True, "health_data": True, "cloud_ai": True},
        "profile": {
            "gender": "MALE", "birth_date": "1996-01-01",
            "height_cm": 175, "weight_kg": 72, "activity_level": 3,
            "goal": "MAINTAIN", "condition_ids": [], "allergen_ids": [],
        },
    }
    r = client.post("/api/v1/auth/register", json=payload)
    assert r.status_code == 201, r.text
    user_test.append(email)
    return r.json()["access_token"], sent, email


def test_register_bang_pin_khong_gui_link_xac_minh(monkeypatch, user_test):
    token, sent, email = _register(monkeypatch, user_test)
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}).json()
    assert me["email"] == email
    assert sent == []


def test_link_xac_minh_cu_van_bam_duoc(monkeypatch, user_test):
    token, _, _ = _register(monkeypatch, user_test)
    user_id = decode_token(token)["sub"]
    r = client.get(f"/api/v1/auth/verify?token={create_verification_token(user_id)}")
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "verified"


def test_verify_bad_token_returns_400():
    r = client.get("/api/v1/auth/verify?token=not-a-real-token")
    assert r.status_code == 400


def test_resend_tra_ve_da_xac_minh(monkeypatch, user_test):
    token, _, _ = _register(monkeypatch, user_test)
    r = client.post("/api/v1/auth/resend-verification", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["status"] == "already_verified"

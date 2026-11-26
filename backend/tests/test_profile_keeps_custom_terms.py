"""Lưu trang Hồ sơ không được xóa dị ứng/bệnh nền tự khai báo.

Lỗi cũ: Profile.jsx luôn gửi custom_conditions=[] và custom_allergens=[] dù trang không có ô
sửa các mục này → mỗi lần bấm Lưu, Warning Engine mất dị ứng người dùng đã gõ lúc đăng ký.
Test gửi đúng payload mà Profile.jsx gửi (không có hai trường đó) và kiểm tra dữ liệu còn nguyên.
"""
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.database import engine
from app.main import app


def _db_up() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _db_up(), reason="Postgres chưa chạy")
client = TestClient(app)


def test_luu_ho_so_khong_xoa_muc_tu_khai_bao(monkeypatch, user_test):
    from app.security import create_pin_verified_token
    email = f"custom_{uuid.uuid4().hex[:10]}@example.com"
    r = client.post("/api/v1/auth/register", json={
        "email": email, "password": "Nutri#Smart2026", "full_name": "Tự Khai Báo",
        "pin_token": create_pin_verified_token(email),
        "consents": {"terms": True, "health_data": True, "cloud_ai": True},
        "profile": {
            "gender": "FEMALE", "birth_date": "1995-05-05", "height_cm": 160, "weight_kg": 55,
            "activity_level": 3, "goal": "MAINTAIN", "condition_ids": [], "allergen_ids": [],
            "custom_conditions": ["Hen phế quản"],
            "custom_allergens": [{"name": "Hạt điều", "severity": "SEVERE"}],
        },
    })
    assert r.status_code == 201, r.text
    user_test.append(email)
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

    # Payload giống hệt saveProfile() trong Profile.jsx
    r = client.put("/api/v1/auth/me", headers=headers, json={
        "full_name": "Tự Khai Báo", "gender": "FEMALE", "birth_date": "1995-05-05",
        "height_cm": 160, "weight_kg": 56, "activity_level": 3, "goal": "LOSE_WEIGHT",
        "condition_ids": [], "allergen_ids": [],
    })
    assert r.status_code == 200, r.text
    p = r.json()["profile"]
    assert p["custom_conditions"] == ["Hen phế quản"]
    assert [a["name"] for a in p["custom_allergens"]] == ["Hạt điều"]

    # Bấm [x] xóa "Hạt điều" trên trang Hồ sơ → Profile.jsx chỉ gửi trường đã đổi
    r = client.put("/api/v1/auth/me", headers=headers, json={"custom_allergens": []})
    assert r.status_code == 200, r.text
    p = r.json()["profile"]
    assert p["custom_allergens"] == [] and p["custom_conditions"] == ["Hen phế quản"]

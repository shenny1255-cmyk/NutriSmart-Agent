"""Tùy chọn "chỉ xử lý bằng AI nội bộ" (kế hoạch ĐATN v2, mục 3 - quyền riêng tư)."""
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.database import engine
from app.main import app
from app.models import UserProfile


def test_cot_ai_local_only_mac_dinh_tat():
    col = UserProfile.__table__.c.ai_local_only
    assert col.nullable is False


def _db_up() -> bool:
    try:
        with engine.connect() as c:
            c.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


@pytest.mark.skipif(not _db_up(), reason="Postgres chưa chạy")
def test_bat_tat_qua_api(user_test):
    client = TestClient(app)
    from app.security import create_pin_verified_token
    email = f"local_{uuid.uuid4().hex[:10]}@example.com"
    r = client.post("/api/v1/auth/register", json={
        "email": email, "password": "Nutri#Smart2026", "full_name": "Người Dùng Thử", "country_code": "VN",
        "pin_token": create_pin_verified_token(email),
        "consents": {"terms": True, "health_data": True, "cloud_ai": True},
        "profile": {"gender": "FEMALE", "birth_date": "1998-01-01", "height_cm": 160, "weight_kg": 55,
                    "activity_level": 3, "goal": "MAINTAIN", "condition_ids": [], "allergen_ids": []},
    })
    assert r.status_code == 201, r.text
    user_test.append(email)
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}

    assert client.get("/api/v1/auth/me", headers=h).json()["profile"]["ai_local_only"] is False
    r = client.put("/api/v1/auth/me", json={"ai_local_only": True}, headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["profile"]["ai_local_only"] is True

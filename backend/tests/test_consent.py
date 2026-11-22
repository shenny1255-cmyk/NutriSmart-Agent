"""Đồng ý xử lý dữ liệu khi đăng ký (kế hoạch ĐATN v2, GĐ1 - Consent; Nghị định 13/2023/NĐ-CP).

- Đồng ý phải rõ ràng, tách theo từng mục đích, không mặc định → API bắt buộc gửi `consents`.
- Điều khoản + xử lý dữ liệu sức khỏe là bắt buộc (không có thì app không tính được calo/cảnh báo).
- Gửi dữ liệu (đã ẩn danh) tới AI đám mây là tùy chọn; từ chối → chỉ dùng AI nội bộ.
- Mỗi lần đồng ý/rút lại được ghi vào user_consents (chỉ thêm, không sửa) làm bằng chứng.
"""
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

import app.routers.auth as auth_module
import app.routers.vision as vision_module
from app.database import SessionLocal, engine
from app.main import app
from app.services import consent


def _db_up() -> bool:
    try:
        with engine.connect() as c:
            c.execute(text("SELECT 1 FROM user_consents LIMIT 1"))
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _db_up(), reason="Postgres tắt hoặc chưa chạy migration 30")
client = TestClient(app)


def _payload(email: str, consents: dict | None) -> dict:
    body = {
        "email": email, "password": "Nutri#Smart2026", "full_name": "Đồng Ý Thử",
        "profile": {"gender": "FEMALE", "birth_date": "1998-01-01", "height_cm": 160, "weight_kg": 55,
                    "activity_level": 3, "goal": "MAINTAIN", "condition_ids": [], "allergen_ids": []},
    }
    if consents is not None:
        body["consents"] = consents
    return body


def _register(monkeypatch, user_test, consents):
    monkeypatch.setattr(auth_module, "send_verification_email", lambda to, link: None)
    email = f"consent_{uuid.uuid4().hex[:10]}@example.com"
    r = client.post("/api/v1/auth/register", json=_payload(email, consents))
    if r.status_code == 201:
        user_test.append(email)
    return r


def _h(r):
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.mark.parametrize("consents", [
    None,                                                       # client cũ không gửi → từ chối
    {"terms": False, "health_data": True, "cloud_ai": True},
    {"terms": True, "health_data": False, "cloud_ai": True},
])
def test_thieu_dong_y_bat_buoc_thi_khong_tao_tai_khoan(monkeypatch, user_test, consents):
    r = _register(monkeypatch, user_test, consents)
    assert r.status_code == 422, r.text


def test_tu_choi_ai_dam_may_thi_chi_dung_ai_noi_bo(monkeypatch, user_test):
    r = _register(monkeypatch, user_test, {"terms": True, "health_data": True, "cloud_ai": False})
    assert r.status_code == 201, r.text
    assert client.get("/api/v1/auth/me", headers=_h(r)).json()["profile"]["ai_local_only"] is True

    rows = client.get("/api/v1/auth/consents", headers=_h(r)).json()
    got = {x["consent_type"]: x["granted"] for x in rows}
    assert got == {"TERMS": True, "HEALTH_DATA": True, "CLOUD_AI": False}
    assert all(x["version"] == consent.CONSENT_VERSION for x in rows)


def test_dong_y_ai_dam_may(monkeypatch, user_test):
    r = _register(monkeypatch, user_test, {"terms": True, "health_data": True, "cloud_ai": True})
    assert r.status_code == 201, r.text
    assert client.get("/api/v1/auth/me", headers=_h(r)).json()["profile"]["ai_local_only"] is False


def test_doi_cong_tac_trong_ho_so_ghi_lai_rut_dong_y(monkeypatch, user_test):
    r = _register(monkeypatch, user_test, {"terms": True, "health_data": True, "cloud_ai": True})
    h = _h(r)
    client.put("/api/v1/auth/me", json={"ai_local_only": True}, headers=h)
    client.put("/api/v1/auth/me", json={"ai_local_only": True}, headers=h)   # không đổi → không ghi thêm
    cloud = [x for x in client.get("/api/v1/auth/consents", headers=h).json() if x["consent_type"] == "CLOUD_AI"]
    assert [x["granted"] for x in cloud] == [False, True]                    # mới nhất trước
    assert cloud[0]["source"] == "PROFILE"


def test_phan_tich_anh_ton_trong_lua_chon_chi_ai_noi_bo(monkeypatch, user_test):
    def _khong_duoc_goi(*a, **k):
        raise AssertionError("Không được gửi ảnh tới Gemini khi người dùng chọn chỉ AI nội bộ")
    monkeypatch.setattr(vision_module, "analyze_food_image", _khong_duoc_goi)
    r = _register(monkeypatch, user_test, {"terms": True, "health_data": True, "cloud_ai": False})
    res = client.post("/api/v1/vision/analyze-meal", headers=_h(r),
                      files={"file": ("a.jpg", b"\xff\xd8fake", "image/jpeg")})
    assert res.status_code == 403
    assert "AI nội bộ" in res.json()["detail"]


def test_phan_tich_anh_ghi_audit_goi_ai_ben_ngoai(monkeypatch, user_test):
    monkeypatch.setattr(vision_module, "analyze_food_image", lambda b, mime_type="image/jpeg": {
        "is_food_image": True, "food_probability": 0.98, "food_name": "Phở bò", "confidence": 0.9, "calories_kcal": 450,
        "protein_g": 20, "carb_g": 60, "fat_g": 10, "description": ""})
    r = _register(monkeypatch, user_test, {"terms": True, "health_data": True, "cloud_ai": True})
    res = client.post("/api/v1/vision/analyze-meal", headers=_h(r),
                      files={"file": ("a.jpg", b"\xff\xd8fake", "image/jpeg")})
    assert res.status_code == 200, res.text
    user_id = client.get("/api/v1/auth/me", headers=_h(r)).json()["id"]
    with SessionLocal() as db:
        after = db.execute(text("""
            SELECT after_data FROM audit_logs WHERE actor_id = :u AND action = 'AI_EXTERNAL_CALL'
        """), {"u": user_id}).scalar()
    assert after["purpose"] == "meal_scan" and after["bytes_sent"] == 6

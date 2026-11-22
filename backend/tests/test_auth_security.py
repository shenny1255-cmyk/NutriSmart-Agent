"""Bảo mật xác thực: đăng nhập đơn thiết bị, mật khẩu mạnh, email không phân biệt hoa thường,
chặn email dùng một lần và honeypot chống bot.

Test cần Postgres; send_verification_email được monkeypatch để không gửi mail thật.
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import text

import app.routers.auth as auth_module
from app.database import SessionLocal, engine
from app.main import app
from app.models import User
from app.schemas import AdminCreateUserIn, RegisterIn
from app.security import create_verification_token, decode_token
from app.services.disposable_emails import is_disposable_email

client = TestClient(app)
STRONG = "Nutri#Smart2026"


def _db_up() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


needs_db = pytest.mark.skipif(not _db_up(), reason="Postgres chưa chạy")


def _payload(email: str, password: str = STRONG, **extra) -> dict:
    return {
        "email": email, "password": password, "full_name": "Bảo Mật",
        "consents": {"terms": True, "health_data": True, "cloud_ai": False},
        "profile": {
            "gender": "FEMALE", "birth_date": "1998-05-05",
            "height_cm": 160, "weight_kg": 52, "activity_level": 2,
            "goal": "MAINTAIN", "condition_ids": [], "allergen_ids": [],
        },
        **extra,
    }


@pytest.fixture(autouse=True)
def _khong_gui_mail(monkeypatch):
    monkeypatch.setattr(auth_module, "send_verification_email", lambda to, link: None)


def _register(user_test, email: str | None = None, **kw):
    email = email or f"sec_{uuid.uuid4().hex[:10]}@example.com"
    r = client.post("/api/v1/auth/register", json=_payload(email, **kw))
    user_test.append(email.strip().lower())
    return r, email


def _login(email: str, password: str = STRONG):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})


def _me(token: str):
    return client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})


# ---------- Test 1: đăng nhập đơn thiết bị ----------

@needs_db
def test_dang_nhap_may_2_vo_hieu_hoa_token_may_1(user_test):
    r, email = _register(user_test)
    assert r.status_code == 201, r.text

    may_1 = _login(email).json()["access_token"]
    assert _me(may_1).status_code == 200

    may_2 = _login(email).json()["access_token"]
    assert decode_token(may_2)["tv"] == decode_token(may_1)["tv"] + 1

    bi_da = _me(may_1)
    assert bi_da.status_code == 401
    assert "thiết bị khác" in bi_da.json()["detail"]
    assert _me(may_2).status_code == 200


@needs_db
def test_token_dang_ky_mat_hieu_luc_sau_khi_dang_nhap_noi_khac(user_test):
    r, email = _register(user_test)
    token_dang_ky = r.json()["access_token"]
    assert _me(token_dang_ky).status_code == 200
    _login(email)
    assert _me(token_dang_ky).status_code == 401


@needs_db
def test_token_xac_minh_email_khong_dung_lam_access_token(user_test):
    r, email = _register(user_test)
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).one()
        verify_token = create_verification_token(str(user.id))
    finally:
        db.close()
    assert _me(verify_token).status_code == 401


# ---------- Test 2 + 3: chính sách mật khẩu ----------

@pytest.mark.parametrize("password, thong_bao", [
    ("Ab1!xyz", "ít nhất 8 ký tự"),
    ("nutri#smart2026", "1 chữ hoa"),
    ("NUTRI#SMART2026", "1 chữ thường"),
    ("Nutri#SmartABC", "1 chữ số"),
    ("NutriSmart2026", "1 ký tự đặc biệt"),
    ("Nutri Smart#2026", "khoảng trắng"),
    ("A1!" + "a" * 62, "64 ký tự"),
    ("Password@123", "quá phổ biến"),
])
def test_mat_khau_yeu_bi_tu_choi_voi_thong_bao_tieng_viet(password, thong_bao):
    with pytest.raises(ValidationError) as exc:
        RegisterIn.model_validate(_payload("user@example.com", password))
    assert thong_bao in str(exc.value)


@needs_db
def test_mat_khau_yeu_qua_api_tra_422(user_test):
    r, _ = _register(user_test, password="password123")
    assert r.status_code == 422
    assert "Mật khẩu cần có ít nhất" in r.text


def test_admin_tao_tai_khoan_cung_ap_dung_mat_khau_manh():
    with pytest.raises(ValidationError):
        AdminCreateUserIn(full_name="Quản Trị", email="staff@gmail.com", password="temporary123", role="EXPERT")
    ok = AdminCreateUserIn(full_name="Quản Trị", email="staff@gmail.com", password=STRONG, role="EXPERT")
    assert ok.password == STRONG


@needs_db
def test_mat_khau_manh_dang_ky_thanh_cong_va_dang_nhap_duoc(user_test):
    r, email = _register(user_test, password="N$9kP!2wZ#8m")
    assert r.status_code == 201, r.text
    assert _login(email, "N$9kP!2wZ#8m").status_code == 200


# ---------- Test 4: email không phân biệt hoa thường ----------

@needs_db
def test_dang_ky_email_hoa_thuong_lan_lon_van_dang_nhap_duoc(user_test):
    goc = f"User_{uuid.uuid4().hex[:6]}@Example.COM"
    r, _ = _register(user_test, email=goc)
    assert r.status_code == 201, r.text
    for bien_the in (goc.lower(), goc.upper(), f"  {goc}  "):
        assert _login(bien_the).status_code == 200, bien_the


@needs_db
def test_dang_nhap_tim_duoc_ca_email_cu_luu_chu_hoa_trong_db(user_test):
    """Dữ liệu cũ có thể lưu email chưa chuẩn hóa; đăng nhập vẫn phải khớp."""
    r, email = _register(user_test)
    hoa = email.upper()
    db = SessionLocal()
    try:
        db.execute(text("UPDATE users SET email = :hoa WHERE email = :e"), {"hoa": hoa, "e": email})
        db.commit()
    finally:
        db.close()
    user_test.append(hoa)
    assert _login(email).status_code == 200


@needs_db
def test_khong_dang_ky_trung_email_khac_hoa_thuong(user_test):
    r, email = _register(user_test)
    assert r.status_code == 201
    r2, _ = _register(user_test, email=email.upper())
    assert r2.status_code == 409


# ---------- Test 5: email dùng một lần ----------

@pytest.mark.parametrize("email", [
    "test@tempmail.com", "test@mailinator.com", "abc@YOPMAIL.com", "x@sub.guerrillamail.com",
])
def test_email_tam_thoi_bi_tu_choi(email):
    assert is_disposable_email(email)
    with pytest.raises(ValidationError) as exc:
        RegisterIn.model_validate(_payload(email))
    assert "email chính thức" in str(exc.value)


def test_email_binh_thuong_khong_bi_chan():
    for email in ("a@gmail.com", "b@hcmut.edu.vn", "c@mailinator.com.vn.example.org"):
        assert not is_disposable_email(email), email


@needs_db
def test_email_tam_thoi_qua_api_tra_422(user_test):
    r, _ = _register(user_test, email=f"bot_{uuid.uuid4().hex[:6]}@mailinator.com")
    assert r.status_code == 422
    assert "email chính thức" in r.text


@needs_db
def test_dang_nhap_khong_chan_email_tam_thoi_cua_tai_khoan_cu():
    """Chặn chỉ áp dụng khi đăng ký; đăng nhập trả 401 bình thường thay vì 422."""
    assert _login("old@mailinator.com", "Whatever#123").status_code == 401


# ---------- Test 6: honeypot ----------

@needs_db
def test_honeypot_co_gia_tri_bi_tu_choi(user_test):
    r, email = _register(user_test, honeypot="https://spam.example")
    assert r.status_code == 400
    assert r.json()["detail"] == "Yêu cầu không hợp lệ"
    db = SessionLocal()
    try:
        assert db.query(User).filter(User.email == email).count() == 0
    finally:
        db.close()


@needs_db
def test_honeypot_rong_van_dang_ky_binh_thuong(user_test):
    r, _ = _register(user_test, honeypot="")
    assert r.status_code == 201, r.text


@needs_db
def test_check_email_bao_som_email_tam_thoi():
    r = client.post("/api/v1/auth/check-email", json={"email": "a@yopmail.com"})
    assert r.json() == {"available": False, "reason": "disposable"}

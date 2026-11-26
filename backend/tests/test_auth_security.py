"""Bảo mật xác thực: đăng nhập đơn thiết bị, mật khẩu mạnh, email không phân biệt hoa thường,
chặn email dùng một lần và honeypot chống bot.

Test cần Postgres; send_pin_email được monkeypatch để không gửi mail thật.
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
from app.security import create_verification_token, create_pin_verified_token, decode_token
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
    monkeypatch.setattr(auth_module, "send_pin_email", lambda to, pin: None)


def _register(user_test, email: str | None = None, **kw):
    email = email or f"sec_{uuid.uuid4().hex[:10]}@example.com"
    kw.setdefault("pin_token", create_pin_verified_token(email))
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


# ---------- Test 5: email dùng một lần / nhà cung cấp không chính thống ----------

@pytest.mark.parametrize("email", [
    "test@tempmail.com", "test@mailinator.com", "abc@YOPMAIL.com", "x@sub.guerrillamail.com",
])
def test_email_tam_thoi_bi_tu_choi(email):
    with pytest.raises(ValidationError) as exc:
        RegisterIn.model_validate(_payload(email))
    assert ("nhà cung cấp chính thống" in str(exc.value)
            or "email chính thức" in str(exc.value))


def test_email_binh_thuong_khong_bi_chan():
    for email in ("a@gmail.com", "b@hcmut.edu.vn", "c@outlook.com"):
        payload = _payload(email)
        m = RegisterIn.model_validate(payload)
        assert m.email == email


@needs_db
def test_email_tam_thoi_qua_api_tra_422(user_test):
    r, _ = _register(user_test, email=f"bot_{uuid.uuid4().hex[:6]}@mailinator.com")
    assert r.status_code == 422
    assert ("nhà cung cấp chính thống" in r.text
            or "email chính thức" in r.text)


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
    res = r.json()
    assert res["available"] is False
    assert res["reason"] in ("not_allowed", "disposable")


@needs_db
def test_chan_email_alias_dau_cong():
    """Chặn user+tag@gmail.com tạo clone."""
    with pytest.raises(ValidationError) as exc:
        RegisterIn.model_validate(_payload("user+alias@gmail.com"))
    assert "dấu '+'" in str(exc.value)


@needs_db
def test_chan_trung_gmail_dau_cham(user_test):
    """n.guyen.an@gmail.com và nguyenan@gmail.com coi là cùng một người."""
    r1, _ = _register(user_test, email="nguyen.an.nutri@gmail.com")
    assert r1.status_code == 201, r1.text

    # Đăng ký lại bỏ dấu chấm -> phải bị từ chối 409
    r2, _ = _register(user_test, email="nguyenannutri@gmail.com")
    assert r2.status_code == 409
    assert "Email đã được sử dụng" in r2.text


@needs_db
def test_tai_khoan_demo_duoc_phep_dang_nhap_da_thiet_bi():
    """Tài khoản demo@nutrismart.vn không bị đá khi nhiều người cùng đăng nhập (bảo vệ đồ án)."""
    r_seed = client.post("/api/v1/demo/seed")
    assert r_seed.status_code == 200
    token1 = r_seed.json()["access_token"]

    # Đăng nhập lần 2 (máy khác)
    r_login2 = client.post("/api/v1/auth/login", json={"email": "demo@nutrismart.vn", "password": "demo1234"})
    assert r_login2.status_code == 200
    token2 = r_login2.json()["access_token"]

    # Cả token 1 và token 2 đều gọi được API /me bình thường
    r_me1 = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token1}"})
    assert r_me1.status_code == 200
    r_me2 = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token2}"})
    assert r_me2.status_code == 200


# ---------- Test 7: xác thực mã PIN email khi đăng ký ----------

@needs_db
def test_dang_ky_khong_co_pin_token_bi_chan_400(user_test):
    r, _ = _register(user_test, pin_token=None)
    assert r.status_code == 400
    assert "mã PIN" in r.json()["detail"]


@needs_db
def test_gui_va_xac_thuc_pin_thanh_cong(monkeypatch, user_test):
    sent = {}
    monkeypatch.setattr(auth_module, "send_pin_email", lambda to, pin: sent.update({"to": to, "pin": pin}))
    email = f"pin_{uuid.uuid4().hex[:8]}@gmail.com"
    try:
        r_send = client.post("/api/v1/auth/send-pin", json={"email": email})
        assert r_send.status_code == 200, r_send.text
        assert sent["to"] == email
        assert len(sent["pin"]) == 6 and sent["pin"].isdigit()

        # Thử sai 1 lần
        r_wrong = client.post("/api/v1/auth/verify-pin", json={"email": email, "pin": "000000" if sent["pin"] != "000000" else "111111"})
        assert r_wrong.status_code == 400
        assert "Còn 4 lần thử" in r_wrong.json()["detail"]

        # Nhập đúng
        r_ok = client.post("/api/v1/auth/verify-pin", json={"email": email, "pin": sent["pin"]})
        assert r_ok.status_code == 200
        pin_token = r_ok.json()["pin_token"]

        # Đăng ký thành công
        r_reg, _ = _register(user_test, email=email, pin_token=pin_token)
        assert r_reg.status_code == 201, r_reg.text
    finally:
        db = SessionLocal()
        try:
            db.execute(text("DELETE FROM email_pins WHERE email = :e"), {"e": email})
            db.commit()
        finally:
            db.close()


@needs_db
def test_gui_lai_pin_trong_60s_bi_chan_429(monkeypatch):
    monkeypatch.setattr(auth_module, "send_pin_email", lambda to, pin: None)
    email = f"cd_{uuid.uuid4().hex[:8]}@gmail.com"
    try:
        assert client.post("/api/v1/auth/send-pin", json={"email": email}).status_code == 200
        r2 = client.post("/api/v1/auth/send-pin", json={"email": email})
        assert r2.status_code == 429
    finally:
        db = SessionLocal()
        try:
            db.execute(text("DELETE FROM email_pins WHERE email = :e"), {"e": email})
            db.commit()
        finally:
            db.close()


@needs_db
def test_xac_thuc_pin_sai_qua_5_lan_bi_khoa(monkeypatch):
    sent = {}
    monkeypatch.setattr(auth_module, "send_pin_email", lambda to, pin: sent.update({"pin": pin}))
    email = f"bf_{uuid.uuid4().hex[:8]}@gmail.com"
    try:
        assert client.post("/api/v1/auth/send-pin", json={"email": email}).status_code == 200
        wrong = "000000" if sent["pin"] != "000000" else "111111"
        for _ in range(5):
            assert client.post("/api/v1/auth/verify-pin", json={"email": email, "pin": wrong}).status_code == 400
        r6 = client.post("/api/v1/auth/verify-pin", json={"email": email, "pin": sent["pin"]})
        assert r6.status_code == 429
    finally:
        db = SessionLocal()
        try:
            db.execute(text("DELETE FROM email_pins WHERE email = :e"), {"e": email})
            db.commit()
        finally:
            db.close()


# ---------- Test 8: chống lạm dụng mã PIN ----------

def _xoa_pin(*emails):
    db = SessionLocal()
    try:
        for e in emails:
            db.execute(text("DELETE FROM email_pins WHERE email = :e"), {"e": e})
            db.execute(text("DELETE FROM pin_send_events WHERE email = :e"), {"e": e})
        db.commit()
    finally:
        db.close()


def _lui_cooldown(email):
    """Giả lập đã qua 60 giây kể từ lần gửi trước."""
    db = SessionLocal()
    try:
        db.execute(text("UPDATE email_pins SET created_at = now() - interval '61 seconds' WHERE email = :e"), {"e": email})
        db.commit()
    finally:
        db.close()


@needs_db
def test_ma_pin_chi_xac_thuc_duoc_mot_lan(monkeypatch):
    sent = {}
    monkeypatch.setattr(auth_module, "send_pin_email", lambda to, pin: sent.update(pin=pin))
    email = f"once_{uuid.uuid4().hex[:8]}@gmail.com"
    try:
        assert client.post("/api/v1/auth/send-pin", json={"email": email}).status_code == 200
        assert client.post("/api/v1/auth/verify-pin", json={"email": email, "pin": sent["pin"]}).status_code == 200
        lan_2 = client.post("/api/v1/auth/verify-pin", json={"email": email, "pin": sent["pin"]})
        assert lan_2.status_code == 400
    finally:
        _xoa_pin(email)


@needs_db
def test_gioi_han_so_lan_gui_pin_moi_gio_cho_mot_email(monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "PIN_SENDS_PER_EMAIL_PER_HOUR", 2)
    monkeypatch.setattr(auth_module, "send_pin_email", lambda to, pin: None)
    email = f"cap_{uuid.uuid4().hex[:8]}@gmail.com"
    try:
        assert client.post("/api/v1/auth/send-pin", json={"email": email}).status_code == 200
        _lui_cooldown(email)
        assert client.post("/api/v1/auth/send-pin", json={"email": email}).status_code == 200
        _lui_cooldown(email)
        r3 = client.post("/api/v1/auth/send-pin", json={"email": email})
        assert r3.status_code == 429
        assert "quá nhiều" in r3.json()["detail"]
    finally:
        _xoa_pin(email)


@needs_db
def test_gioi_han_so_lan_gui_pin_moi_gio_theo_ip(monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "PIN_SENDS_PER_IP_PER_HOUR", 2)
    monkeypatch.setattr(settings, "TRUST_PROXY_HEADERS", True)
    monkeypatch.setattr(auth_module, "send_pin_email", lambda to, pin: None)
    ip = f"203.0.113.{uuid.uuid4().int % 250 + 1}"
    emails = [f"ip{i}_{uuid.uuid4().hex[:8]}@gmail.com" for i in range(3)]
    headers = {"X-Forwarded-For": f"{ip}, 10.0.0.1"}
    db = SessionLocal()
    db.execute(text("DELETE FROM pin_send_events WHERE ip = :ip"), {"ip": ip})
    db.commit()
    db.close()
    try:
        assert client.post("/api/v1/auth/send-pin", json={"email": emails[0]}, headers=headers).status_code == 200
        assert client.post("/api/v1/auth/send-pin", json={"email": emails[1]}, headers=headers).status_code == 200
        r3 = client.post("/api/v1/auth/send-pin", json={"email": emails[2]}, headers=headers)
        assert r3.status_code == 429
        # IP khác vẫn gửi được
        other = client.post("/api/v1/auth/send-pin", json={"email": emails[2]}, headers={"X-Forwarded-For": "198.51.100.7"})
        assert other.status_code == 200
    finally:
        _xoa_pin(*emails)


def test_bo_qua_x_forwarded_for_khi_khong_tin_proxy(monkeypatch):
    from app.config import settings
    from starlette.requests import Request
    monkeypatch.setattr(settings, "TRUST_PROXY_HEADERS", False)
    req = Request({"type": "http", "headers": [(b"x-forwarded-for", b"1.2.3.4")], "client": ("9.9.9.9", 1)})
    assert auth_module._client_ip(req) == "9.9.9.9"
    monkeypatch.setattr(settings, "TRUST_PROXY_HEADERS", True)
    assert auth_module._client_ip(req) == "1.2.3.4"


def test_smtp_loi_khong_ghi_ma_pin_vao_log(monkeypatch, caplog):
    import logging
    import app.services.email as email_service
    from app.config import settings
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.example.com")

    def _hong(*a, **kw):
        raise OSError("connection refused")
    monkeypatch.setattr(email_service.smtplib, "SMTP", _hong)
    with caplog.at_level(logging.INFO, logger="nutrismart.email"):
        email_service.send_pin_email("x@gmail.com", "482913")
    assert "482913" not in caplog.text
    assert "thất bại" in caplog.text


@needs_db
def test_dang_ky_bang_pin_khong_gui_them_link_xac_minh(monkeypatch, user_test):
    import app.services.email as email_service
    goi = []
    monkeypatch.setattr(email_service, "send_verification_email", lambda to, link: goi.append(to))
    r, _ = _register(user_test)
    assert r.status_code == 201, r.text
    assert goi == []


@needs_db
def test_ma_pin_bo_do_qua_1_gio_duoc_don(monkeypatch):
    monkeypatch.setattr(auth_module, "send_pin_email", lambda to, pin: None)
    cu = f"old_{uuid.uuid4().hex[:8]}@gmail.com"
    moi = f"new_{uuid.uuid4().hex[:8]}@gmail.com"
    db = SessionLocal()
    try:
        db.execute(text(
            "INSERT INTO email_pins (email, pin_hash, attempts, expires_at, created_at) "
            "VALUES (:e, 'x', 0, now() - interval '110 minutes', now() - interval '2 hours')"
        ), {"e": cu})
        db.commit()
        assert client.post("/api/v1/auth/send-pin", json={"email": moi}).status_code == 200
        con_lai = db.execute(text("SELECT count(*) FROM email_pins WHERE email = :e"), {"e": cu}).scalar()
        assert con_lai == 0
    finally:
        db.close()
        _xoa_pin(cu, moi)

"""Tìm kiếm người dùng ở màn Quản trị: theo HỌ TÊN hoặc email, bỏ qua dấu tiếng Việt."""
import uuid

import pytest
from sqlalchemy import text

from app.database import SessionLocal, engine
from app.models import User
from app.routers.admin import search_users


def _db_up() -> bool:
    try:
        with engine.connect() as c:
            c.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _db_up(), reason="Cần Postgres để chạy")


@pytest.fixture
def ba_nguoi_dung():
    """3 tài khoản có dấu, dọn sạch sau test."""
    db = SessionLocal()
    hau_to = uuid.uuid4().hex[:8]
    ho_so = [
        ("Nguyễn Văn An", f"an-{hau_to}@test.local"),
        ("Trần Thị Bích", f"bich-{hau_to}@test.local"),
        ("Lê Minh Quang", f"quang-{hau_to}@test.local"),
    ]
    for ten, email in ho_so:
        db.add(User(email=email, password_hash="x", full_name=ten, role="USER"))
    db.commit()

    yield db, hau_to

    db.execute(text("DELETE FROM users WHERE email LIKE :p"), {"p": f"%-{hau_to}@test.local"})
    db.commit()
    db.close()


def _ten(rows):
    return [u.full_name for u in rows]


def test_tim_theo_ho_ten_co_dau(ba_nguoi_dung):
    db, _ = ba_nguoi_dung
    assert "Nguyễn Văn An" in _ten(search_users(db, "Nguyễn Văn"))


def test_tim_theo_ho_ten_go_khong_dau(ba_nguoi_dung):
    db, _ = ba_nguoi_dung
    assert "Nguyễn Văn An" in _ten(search_users(db, "nguyen van"))


def test_tim_khong_phan_biet_hoa_thuong(ba_nguoi_dung):
    db, _ = ba_nguoi_dung
    assert "Trần Thị Bích" in _ten(search_users(db, "TRAN THI"))


def test_van_tim_duoc_theo_email(ba_nguoi_dung):
    db, hau_to = ba_nguoi_dung
    assert "Lê Minh Quang" in _ten(search_users(db, f"quang-{hau_to}"))


def test_khong_khop_thi_tra_ve_rong(ba_nguoi_dung):
    db, hau_to = ba_nguoi_dung
    ket_qua = [u for u in search_users(db, f"khongtontai-{hau_to}")]
    assert ket_qua == []


def test_khong_nhap_gi_thi_tra_ve_tat_ca(ba_nguoi_dung):
    db, _ = ba_nguoi_dung
    tat_ca = _ten(search_users(db, None))
    assert "Nguyễn Văn An" in tat_ca and "Trần Thị Bích" in tat_ca


def test_email_domain_la_van_serialize_duoc():
    """Bản ghi cũ có domain dành riêng (.local, .test...) không được làm hỏng cả danh sách."""
    import datetime as _dt

    from app.schemas import AdminUserOut

    out = AdminUserOut.model_validate({
        "id":         uuid.uuid4(),
        "email":      "cat-818813fe@test.local",
        "full_name":  "Quản trị test",
        "role":       "ADMIN",
        "is_active":  True,
        "created_at": _dt.datetime.now(_dt.timezone.utc),
        "updated_at": _dt.datetime.now(_dt.timezone.utc),
    })
    assert out.email == "cat-818813fe@test.local"

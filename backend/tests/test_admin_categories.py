"""CRUD danh mục tài liệu / danh mục thuốc và upload tài liệu (task 14)."""
import uuid

import pytest
from sqlalchemy import text

from app.database import SessionLocal, engine
from app.services.slug import tao_slug
from app.services.doc_upload import doc_text_tu_file, LoaiFileKhongHoTro


def _db_up() -> bool:
    try:
        with engine.connect() as c:
            c.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


# ---------- Logic thuần: sinh slug ----------

def test_slug_bo_dau_tieng_viet():
    assert tao_slug("Dinh dưỡng cho người tiểu đường") == "dinh-duong-cho-nguoi-tieu-duong"


def test_slug_xu_ly_chu_d_gach_ngang():
    assert tao_slug("Đái tháo đường") == "dai-thao-duong"


def test_slug_bo_ky_tu_dac_biet_va_khoang_trang_thua():
    assert tao_slug("  Tim mạch & Huyết áp (2026)!  ") == "tim-mach-huyet-ap-2026"


def test_slug_rong_thi_tra_ve_chuoi_thay_the():
    assert tao_slug("!!!") == "danh-muc"
    assert tao_slug("") == "danh-muc"


# ---------- Logic thuần: bóc text từ file upload ----------

def test_doc_file_txt():
    assert "xin chào" in doc_text_tu_file("ghi-chu.txt", "xin chào".encode("utf-8")).lower()


def test_doc_file_markdown():
    assert "tiêu đề" in doc_text_tu_file("bai.md", "# Tiêu đề\nnội dung".encode("utf-8")).lower()


def test_tu_choi_dinh_dang_khong_ho_tro():
    with pytest.raises(LoaiFileKhongHoTro):
        doc_text_tu_file("anh.png", b"\x89PNG")


def test_doc_file_pdf():
    from pypdf import PdfWriter
    import io
    # PDF rỗng vẫn phải bóc được (0 ký tự) chứ không được ném lỗi định dạng
    w = PdfWriter()
    w.add_blank_page(width=200, height=200)
    buf = io.BytesIO()
    w.write(buf)
    assert doc_text_tu_file("tai-lieu.pdf", buf.getvalue()) == ""


# ---------- Tích hợp ----------

pytestmark_db = pytest.mark.skipif(not _db_up(), reason="Cần Postgres để chạy")


@pytest.fixture
def db():
    s = SessionLocal()
    yield s
    s.rollback()
    s.close()


@pytest.fixture
def admin(db):
    from app.models import User, UserProfile
    u = User(email=f"cat-{uuid.uuid4().hex[:8]}@test.local", password_hash="x", role="ADMIN")
    db.add(u)
    db.flush()
    db.add(UserProfile(user_id=u.id, full_name="Quản trị test"))
    db.commit()
    yield u
    # audit_logs.actor_id không có ON DELETE nên phải dọn nhật ký kiểm toán trước
    db.execute(text("DELETE FROM audit_logs WHERE actor_id = :i"), {"i": str(u.id)})
    db.execute(text("DELETE FROM users WHERE id = :i"), {"i": str(u.id)})
    db.commit()


@pytestmark_db
def test_them_va_liet_ke_danh_muc_tai_lieu(db, admin):
    from app.routers.admin import them_doc_category, danh_sach_doc_category, xoa_doc_category
    from app.schemas import CategoryIn

    dm = them_doc_category(db, admin, CategoryIn(name="Bệnh tim mạch"))
    assert dm.slug == "benh-tim-mach"
    assert any(x.id == dm.id for x in danh_sach_doc_category(db))

    xoa_doc_category(db, admin, dm.id)
    assert not any(x.id == dm.id for x in danh_sach_doc_category(db))


@pytestmark_db
def test_trung_ten_thi_slug_tu_them_hau_to(db, admin):
    from app.routers.admin import them_doc_category, xoa_doc_category
    from app.schemas import CategoryIn

    a = them_doc_category(db, admin, CategoryIn(name="Nội tiết"))
    b = them_doc_category(db, admin, CategoryIn(name="Nội tiết"))
    try:
        assert a.slug == "noi-tiet"
        assert b.slug != a.slug and b.slug.startswith("noi-tiet")
    finally:
        xoa_doc_category(db, admin, a.id)
        xoa_doc_category(db, admin, b.id)


@pytestmark_db
def test_xoa_danh_muc_khong_lam_mat_tai_lieu(db, admin):
    from app.models import Document
    from app.routers.admin import them_doc_category, xoa_doc_category
    from app.schemas import CategoryIn

    dm = them_doc_category(db, admin, CategoryIn(name="Danh mục tạm"))
    doc = Document(title="Tài liệu thuộc danh mục tạm", raw_text="nội dung",
                   status="PENDING", category_id=dm.id, uploaded_by=admin.id)
    db.add(doc)
    db.commit()

    xoa_doc_category(db, admin, dm.id)
    db.refresh(doc)
    assert doc.id is not None and doc.category_id is None   # tài liệu còn, chỉ mất danh mục

    db.execute(text("DELETE FROM documents WHERE id = :i"), {"i": str(doc.id)})
    db.commit()





@pytestmark_db
def test_upload_tai_lieu_tao_ban_ghi_cho_duyet(db, admin):
    from app.models import Document
    from app.routers.expert import luu_tai_lieu_upload

    doc = luu_tai_lieu_upload(
        db, admin,
        title="Hướng dẫn dinh dưỡng nội bộ",
        raw_text="Nội dung tài liệu do chuyên gia tải lên." * 5,
        category_id=None,
        source_name="Tải lên thủ công",
    )
    try:
        assert doc.status == "PENDING"          # phải qua duyệt mới vào RAG
        assert doc.uploaded_by == admin.id
        assert "chuyên gia" in doc.raw_text
    finally:
        db.execute(text("DELETE FROM documents WHERE id = :i"), {"i": str(doc.id)})
        db.commit()


@pytestmark_db
def test_upload_tu_choi_noi_dung_qua_ngan(db, admin):
    from fastapi import HTTPException
    from app.routers.expert import luu_tai_lieu_upload

    with pytest.raises(HTTPException) as e:
        luu_tai_lieu_upload(db, admin, title="Ngắn", raw_text="vài chữ",
                            category_id=None, source_name=None)
    assert e.value.status_code == 400

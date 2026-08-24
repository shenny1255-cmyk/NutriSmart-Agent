"""Kho bài viết — test theo TDD (spec 2026-08-24)."""
import uuid
from datetime import datetime, timezone, timedelta

import pytest
from sqlalchemy import text

from app.database import SessionLocal, engine
from app.routers.articles import make_excerpt


def _db_up() -> bool:
    try:
        with engine.connect() as c:
            c.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


# ---------- Logic thuần: hàm excerpt ----------

def test_excerpt_chuoi_rong():
    assert make_excerpt("") == ""
    assert make_excerpt(None) == ""


def test_excerpt_noi_dung_ngan():
    assert make_excerpt("Rau xanh tốt cho sức khỏe") == "Rau xanh tốt cho sức khỏe"


def test_excerpt_noi_dung_dai():
    text_long = "A" * 300
    result = make_excerpt(text_long)
    assert len(result) <= 221  # 220 + "…"
    assert result.endswith("…")


def test_excerpt_cat_tai_ranh_gioi_tu():
    words = "từ " * 120  # dài hơn 220
    result = make_excerpt(words)
    assert result.endswith("…")
    assert len(result) <= 221


def test_excerpt_thay_khoang_trang_lien_tiep():
    assert make_excerpt("  nhiều   khoảng    trắng  ") == "nhiều khoảng trắng"


# ---------- Tích hợp ----------

pytestmark_db = pytest.mark.skipif(not _db_up(), reason="Cần Postgres để chạy")


@pytest.fixture
def db():
    s = SessionLocal()
    yield s
    s.rollback()
    s.close()



def _make_user(db, role="USER"):
    from app.models import User, UserProfile
    from app.security import create_access_token
    u = User(email=f"art-{uuid.uuid4().hex[:8]}@test.local", password_hash="x", role=role)
    db.add(u)
    db.flush()
    db.add(UserProfile(user_id=u.id, full_name=f"Test {role}"))
    db.commit()
    return u, create_access_token(str(u.id))


def _cleanup_user(db, user):
    db.execute(text("DELETE FROM audit_logs WHERE actor_id = :i"), {"i": str(user.id)})
    db.execute(text("DELETE FROM users WHERE id = :i"), {"i": str(user.id)})
    db.commit()


def _client():
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


@pytest.fixture
def admin_tok(db):
    u, t = _make_user(db, "ADMIN")
    yield u, t
    _cleanup_user(db, u)


@pytest.fixture
def sample_docs(db, admin_tok):
    from app.models import DocCategory, Document
    admin, _ = admin_tok
    cat = DocCategory(name=f"TC-{uuid.uuid4().hex[:6]}", slug=f"tc-{uuid.uuid4().hex[:6]}")
    db.add(cat)
    db.flush()
    now = datetime.now(timezone.utc)
    docs = []
    for i in range(3):
        d = Document(
            title=f"Bài viết test {i}", raw_text="Nội dung bài viết khá dài " * 20,
            source_name="Nguồn Test", source_url=f"https://example.com/{i}" if i < 2 else None,
            status="APPROVED", category_id=cat.id, uploaded_by=admin.id,
            approved_by=admin.id, approved_at=now - timedelta(hours=i),
        )
        db.add(d); docs.append(d)
    pending = Document(title="Bài chờ duyệt", raw_text="Pending", status="PENDING",
                       category_id=cat.id, uploaded_by=admin.id)
    db.add(pending); docs.append(pending)
    deleted = Document(title="Bài đã xóa", raw_text="Deleted", status="APPROVED",
                       category_id=cat.id, uploaded_by=admin.id, approved_by=admin.id,
                       approved_at=now, deleted_at=now)
    db.add(deleted); docs.append(deleted)
    db.commit()
    yield cat, docs
    for d in docs:
        db.execute(text("DELETE FROM documents WHERE id = :i"), {"i": str(d.id)})
    db.execute(text("DELETE FROM doc_categories WHERE id = :i"), {"i": cat.id})


@pytestmark_db
def test_moi_role_deu_truy_cap_duoc(db, admin_tok, sample_docs):
    client = _client()
    for role in ("USER", "EXPERT", "ADMIN"):
        u, t = _make_user(db, role)
        try:
            r = client.get("/api/v1/articles", headers={"Authorization": f"Bearer {t}"})
            assert r.status_code == 200, f"{role} bị từ chối"
        finally:
            _cleanup_user(db, u)


@pytestmark_db
def test_chua_dang_nhap_bi_tu_choi(db, sample_docs):
    assert _client().get("/api/v1/articles").status_code == 401


@pytestmark_db
def test_chi_approved_chua_xoa(db, admin_tok, sample_docs):
    _, token = admin_tok
    r = _client().get("/api/v1/articles?page_size=48", headers={"Authorization": f"Bearer {token}"})
    titles = [i["title"] for i in r.json()["items"]]
    assert any("Bài viết test" in t for t in titles)
    assert "Bài chờ duyệt" not in titles
    assert "Bài đã xóa" not in titles


@pytestmark_db
def test_khong_co_raw_text(db, admin_tok, sample_docs):
    _, token = admin_tok
    r = _client().get("/api/v1/articles", headers={"Authorization": f"Bearer {token}"})
    for item in r.json()["items"]:
        assert "raw_text" not in item
        assert "file_path" not in item
        assert "uploaded_by" not in item


@pytestmark_db
def test_search_khong_phan_biet_hoa_thuong(db, admin_tok, sample_docs):
    _, token = admin_tok
    h = {"Authorization": f"Bearer {token}"}
    assert _client().get("/api/v1/articles?q=BÀI VIẾT TEST", headers=h).json()["total"] >= 1
    assert _client().get("/api/v1/articles?q=nguồn test", headers=h).json()["total"] >= 1


@pytestmark_db
def test_loc_danh_muc_va_ket_hop(db, admin_tok, sample_docs):
    _, token = admin_tok
    cat, _ = sample_docs
    h = {"Authorization": f"Bearer {token}"}
    assert _client().get(f"/api/v1/articles?category_id={cat.id}", headers=h).json()["total"] == 3
    r = _client().get("/api/v1/articles?category_id=999999", headers=h)
    assert r.status_code == 200 and r.json()["total"] == 0


@pytestmark_db
def test_pagination_format(db, admin_tok, sample_docs):
    _, token = admin_tok
    cat, _ = sample_docs
    h = {"Authorization": f"Bearer {token}"}
    data = _client().get(f"/api/v1/articles?category_id={cat.id}&page=1&page_size=6", headers=h).json()
    assert data["page"] == 1 and data["page_size"] == 6 and data["total"] == 3


@pytestmark_db
def test_categories_chi_dem_approved(db, admin_tok, sample_docs):
    _, token = admin_tok
    cat, _ = sample_docs
    data = _client().get("/api/v1/articles/categories", headers={"Authorization": f"Bearer {token}"}).json()
    matched = [c for c in data if c["id"] == cat.id]
    assert len(matched) == 1 and matched[0]["article_count"] == 3


@pytestmark_db
def test_thieu_source_url_category_approved_at(db, admin_tok):
    from app.models import Document
    admin, token = admin_tok
    doc = Document(title="Bài không danh mục", raw_text="Nội dung", status="APPROVED",
                   source_url=None, source_name=None, category_id=None,
                   uploaded_by=admin.id, approved_at=None)
    db.add(doc); db.commit()
    try:
        items = _client().get("/api/v1/articles?q=Bài không danh mục",
                              headers={"Authorization": f"Bearer {token}"}).json()["items"]
        m = [i for i in items if i["title"] == "Bài không danh mục"]
        assert len(m) == 1
        assert m[0]["category"] is None and m[0]["source_url"] is None and m[0]["approved_at"] is None
    finally:
        db.execute(text("DELETE FROM documents WHERE id = :i"), {"i": str(doc.id)})
        db.commit()

    db.commit()

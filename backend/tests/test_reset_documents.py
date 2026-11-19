"""Nút "Reset danh sách để Demo": chỉ Admin được dùng và không được xóa lịch sử chat.

Mọi thao tác chạy trong một transaction được rollback, nên dữ liệu thật trong DB dev không bị xóa.
"""
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import engine
from app.deps import get_db
from app.main import app
from app.models import ChatMessage, ChatSession, Document, User
from app.security import create_access_token


def _db_up() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


@pytest.fixture
def rolled_back_db():
    conn = engine.connect()
    outer = conn.begin()
    db = Session(bind=conn, join_transaction_mode="create_savepoint")
    app.dependency_overrides[get_db] = lambda: db
    try:
        yield db
    finally:
        app.dependency_overrides.pop(get_db, None)
        db.close()
        outer.rollback()
        conn.close()


def _user(db, role: str) -> dict:
    user = User(email=f"reset-{uuid.uuid4().hex[:8]}@test.local", password_hash="x", role=role)
    db.add(user)
    db.flush()
    return {"user": user, "headers": {"Authorization": f"Bearer {create_access_token(str(user.id))}"}}


@pytest.mark.skipif(not _db_up(), reason="Cần Postgres để chạy")
def test_expert_khong_duoc_reset_tai_lieu(rolled_back_db):
    db = rolled_back_db
    expert = _user(db, "EXPERT")
    before = db.query(Document).count()
    r = TestClient(app).post("/api/v1/expert/documents/reset", headers=expert["headers"])
    assert r.status_code == 403
    assert db.query(Document).count() == before


@pytest.mark.skipif(not _db_up(), reason="Cần Postgres để chạy")
def test_admin_reset_giu_nguyen_lich_su_chat(rolled_back_db):
    db = rolled_back_db
    admin = _user(db, "ADMIN")
    session = ChatSession(user_id=admin["user"].id)
    db.add(session)
    db.flush()
    db.add(ChatMessage(session_id=session.id, role="user", content="Tin nhắn phải được giữ lại"))
    db.add(Document(title="Tài liệu sẽ bị reset", status="PENDING", raw_text="x"))
    db.flush()
    chats_before = db.query(ChatMessage).count()

    r = TestClient(app).post("/api/v1/expert/documents/reset", headers=admin["headers"])
    assert r.status_code == 200, r.text
    assert db.query(Document).count() == 0
    assert db.query(ChatMessage).count() == chats_before

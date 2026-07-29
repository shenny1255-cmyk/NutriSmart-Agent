"""Fixture dùng chung cho test.

Nhiều test phải đăng ký tài khoản thật qua API. Không dọn thì chúng đọng lại trong
DB và hiện lên màn Quản lý người dùng của admin (đó là lý do trước đây GET
/admin/users phải tự chạy DELETE — một API đọc mà lại xóa dữ liệu).
File test nào tạo user thì xin fixture `user_test` và append email vào đó.
"""

import pytest
from sqlalchemy import text

from app.database import SessionLocal


@pytest.fixture
def user_test():
    """Bộ gom email test — append vào đây, cuối test tự xóa (kể cả khi test fail)."""
    emails: list[str] = []
    yield emails

    ds = [e for e in emails if e]
    if not ds:
        return

    db = SessionLocal()
    try:
        # audit_logs.actor_id không có ON DELETE nên phải dọn nhật ký kiểm toán trước;
        # các bảng còn lại (health_profiles, chat_sessions, meal_logs...) đều CASCADE.
        db.execute(text("""
            DELETE FROM audit_logs
             WHERE actor_id IN (SELECT id FROM users WHERE email = ANY(CAST(:e AS text[])))
        """), {"e": ds})
        db.execute(text("DELETE FROM users WHERE email = ANY(CAST(:e AS text[]))"), {"e": ds})
        db.commit()
    finally:
        db.close()

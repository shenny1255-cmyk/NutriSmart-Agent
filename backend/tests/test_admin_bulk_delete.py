import uuid
from datetime import date, timedelta

import pytest
from fastapi import HTTPException
from pydantic import ValidationError


def test_bulk_delete_yeu_cau_it_nhat_mot_user_id():
    from app.schemas import BulkDeleteUsersIn

    with pytest.raises(ValidationError):
        BulkDeleteUsersIn(user_ids=[])


def test_bulk_delete_loai_id_trung_lap():
    from app.schemas import BulkDeleteUsersIn

    user_id = uuid.uuid4()
    payload = BulkDeleteUsersIn(user_ids=[user_id, user_id])
    assert payload.user_ids == [user_id]


def test_admin_khong_duoc_tu_ha_quyen():
    from app.routers.admin import ensure_role_change_allowed

    actor_id = uuid.uuid4()
    with pytest.raises(HTTPException) as exc:
        ensure_role_change_allowed(actor_id, actor_id, "EXPERT")
    assert exc.value.status_code == 400


def test_admin_van_duoc_giu_nguyen_vai_tro_cua_minh():
    from app.routers.admin import ensure_role_change_allowed

    actor_id = uuid.uuid4()
    ensure_role_change_allowed(actor_id, actor_id, "ADMIN")


def test_admin_create_user_chuan_hoa_email_va_validate_du_lieu():
    from app.schemas import AdminCreateUserIn

    payload = AdminCreateUserIn(
        full_name="Nguyễn Văn An",
        email="  NEW.USER@GMAIL.COM ",
        password="temporary123",
        role="EXPERT",
    )
    assert str(payload.email) == "new.user@gmail.com"

    with pytest.raises(ValidationError):
        AdminCreateUserIn(full_name="@@", email="bad", password="short", role="ADMIN")

    with pytest.raises(ValidationError):
        AdminCreateUserIn(
            full_name="Nguyễn Văn An", email="user@example.com",
            password="temporary123", role="USER",
        )


def test_validate_khoang_ngay_audit():
    from app.routers.admin import validate_audit_date_range

    validate_audit_date_range(date.today() - timedelta(days=7), date.today())
    with pytest.raises(HTTPException):
        validate_audit_date_range(date.today(), date.today() - timedelta(days=1))
    with pytest.raises(HTTPException):
        validate_audit_date_range(None, date.today() + timedelta(days=1))

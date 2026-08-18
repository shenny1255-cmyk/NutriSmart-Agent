from app.models import RolePermission, StaffProfile, User


PERMISSION_COLUMNS = {
    "can_manage_users",
    "can_manage_foods",
    "can_manage_categories",
    "can_review_documents",
    "can_review_plans",
    "can_review_ai_chat",
    "can_review_logs",
    "can_manage_permissions",
}


def test_quyen_duoc_gan_theo_role_thay_vi_nhan_vien():
    assert RolePermission.__tablename__ == "role_permissions"
    assert "role" in RolePermission.__table__.primary_key.columns
    assert "user_id" not in RolePermission.__table__.columns
    assert PERMISSION_COLUMNS <= set(RolePermission.__table__.columns.keys())


def test_staff_profile_khong_con_so_huu_quyen_rieng():
    assert not hasattr(StaffProfile, "permissions")


def test_user_lay_quyen_theo_role():
    relationship = User.__mapper__.relationships["role_permission"]

    assert relationship.uselist is False

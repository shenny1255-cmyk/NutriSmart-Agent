from app.models import User, UserProfile


def test_ho_so_nguoi_dung_co_ten_dong_bo():
    assert UserProfile.__tablename__ == "user_profile"
    assert "profile" in User.__mapper__.relationships
    assert "info" not in User.__mapper__.relationships


def test_user_profile_dung_user_id_lam_khoa_chinh():
    assert {column.name for column in UserProfile.__table__.primary_key} == {"user_id"}

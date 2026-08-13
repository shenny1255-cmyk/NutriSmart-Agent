from app.models import ActivityLevel, UserProfile
from app.services import calorie


def test_danh_muc_muc_do_van_dong_khong_can_code():
    assert set(ActivityLevel.__table__.columns.keys()) == {
        "id", "name", "description", "calorie_multiplier"
    }


def test_user_profile_tham_chieu_danh_muc_bang_khoa_ngoai():
    assert "activity_level" not in UserProfile.__table__.columns
    column = UserProfile.__table__.columns["activity_level_id"]

    assert {str(fk.target_fullname) for fk in column.foreign_keys} == {
        "activity_levels.id"
    }


def test_cong_thuc_calorie_nhan_he_so_tu_danh_muc():
    assert not hasattr(calorie, "ACTIVITY_FACTOR")
    result = calorie.daily_calorie_target(
        gender="MALE",
        birth_date=__import__("datetime").date(2000, 1, 1),
        height_cm=170,
        weight_kg=70,
        activity_multiplier=1.2,
        goal="MAINTAIN",
    )

    assert result >= 1500

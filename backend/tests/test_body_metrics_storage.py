from app.models import BodyMetricHistory, UserProfile
from app.routers.auth import _profile_out


def test_so_do_co_the_chi_duoc_luu_trong_bang_lich_su():
    assert "height_cm" not in UserProfile.__table__.columns
    assert "weight_kg" not in UserProfile.__table__.columns
    assert "height_cm" in BodyMetricHistory.__table__.columns
    assert "weight_kg" in BodyMetricHistory.__table__.columns


def test_bmi_duoc_tinh_tu_so_do_cua_tung_moc():
    metric = BodyMetricHistory(height_cm=170, weight_kg=68)

    assert metric.bmi == 23.53


def test_api_ho_so_van_giu_nguyen_cau_truc_cho_frontend():
    info = UserProfile(
        gender="MALE",
        activity_level=3,
        goal="MAINTAIN",
        custom_conditions=[],
        custom_allergens=[],
    )
    metric = BodyMetricHistory(height_cm=170, weight_kg=68)

    profile = _profile_out(info, metric)

    assert profile.height_cm == 170
    assert profile.weight_kg == 68
    assert profile.bmi == 23.53

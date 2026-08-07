import pytest
from pydantic import ValidationError

from app.schemas import ProfileIn, UserProfileUpdateIn


def profile_data(height_cm=170, weight_kg=65):
    return {
        "gender": "MALE", "birth_date": "2000-01-01",
        "height_cm": height_cm, "weight_kg": weight_kg,
        "activity_level": 3, "goal": "MAINTAIN",
    }


@pytest.mark.parametrize("height_cm,weight_kg", [(111, 300), (249, 20)])
def test_dang_ky_tu_choi_to_hop_chieu_cao_can_nang_bat_thuong(height_cm, weight_kg):
    with pytest.raises(ValidationError, match="BMI"):
        ProfileIn(**profile_data(height_cm, weight_kg))


def test_cap_nhat_tu_choi_to_hop_chieu_cao_can_nang_bat_thuong():
    with pytest.raises(ValidationError, match="BMI"):
        UserProfileUpdateIn(height_cm=111, weight_kg=300)


def test_chap_nhan_to_hop_chieu_cao_can_nang_hop_ly():
    assert ProfileIn(**profile_data()).weight_kg == 65
    assert UserProfileUpdateIn(height_cm=170, weight_kg=65).height_cm == 170

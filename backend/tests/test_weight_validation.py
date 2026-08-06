import pytest
from pydantic import ValidationError

from app.schemas import ProfileIn, UserProfileUpdateIn, WeightIn


def _profile_data(weight_kg: float) -> dict:
    return {
        "gender": "MALE",
        "birth_date": "2000-01-01",
        "height_cm": 170,
        "weight_kg": weight_kg,
        "activity_level": 3,
        "goal": "MAINTAIN",
    }


@pytest.mark.parametrize("weight_kg", [19.9, 300.1])
def test_rejects_weight_outside_logical_range(weight_kg: float):
    with pytest.raises(ValidationError):
        ProfileIn(**_profile_data(weight_kg))
    with pytest.raises(ValidationError):
        UserProfileUpdateIn(weight_kg=weight_kg)
    with pytest.raises(ValidationError):
        WeightIn(weight_kg=weight_kg)


@pytest.mark.parametrize("weight_kg", [20, 300])
def test_accepts_weight_boundary_values(weight_kg: float):
    assert ProfileIn(**_profile_data(weight_kg)).weight_kg == weight_kg
    assert UserProfileUpdateIn(weight_kg=weight_kg).weight_kg == weight_kg
    assert WeightIn(weight_kg=weight_kg).weight_kg == weight_kg

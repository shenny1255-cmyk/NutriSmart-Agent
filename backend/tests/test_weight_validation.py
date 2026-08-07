import pytest
from pydantic import ValidationError

from app.schemas import ProfileIn, UserProfileUpdateIn, WeightIn


def _profile_data(weight_kg: float, height_cm: float = 170) -> dict:
    return {
        "gender": "MALE",
        "birth_date": "2000-01-01",
        "height_cm": height_cm,
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


@pytest.mark.parametrize("weight_kg,height_cm", [(20, 140), (300, 200)])
def test_accepts_weight_boundary_values_when_bmi_is_plausible(weight_kg: float, height_cm: float):
    assert ProfileIn(**_profile_data(weight_kg, height_cm)).weight_kg == weight_kg
    assert UserProfileUpdateIn(weight_kg=weight_kg).weight_kg == weight_kg
    assert WeightIn(weight_kg=weight_kg).weight_kg == weight_kg

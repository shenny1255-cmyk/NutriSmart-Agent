import pytest
from pydantic import ValidationError

from app.schemas import RegisterIn, UserProfileUpdateIn


def _register_data(full_name: str) -> dict:
    return {
        "email": "name@example.com",
        "password": "password123",
        "full_name": full_name,
        "profile": {
            "gender": "MALE",
            "birth_date": "2000-01-01",
            "height_cm": 170,
            "weight_kg": 65,
            "activity_level": 3,
            "goal": "MAINTAIN",
        },
    }


@pytest.mark.parametrize("full_name", ["A", "Nguyễn 123", "@@@", "An 😊", "An--Bình"])
def test_rejects_illogical_full_name(full_name: str):
    with pytest.raises(ValidationError):
        RegisterIn(**_register_data(full_name))
    with pytest.raises(ValidationError):
        UserProfileUpdateIn(full_name=full_name)


@pytest.mark.parametrize("full_name", ["Nguyễn Văn An", "Jean-Luc O'Neill", "Lê Ý"])
def test_accepts_and_normalizes_valid_full_name(full_name: str):
    assert RegisterIn(**_register_data(f"  {full_name}  ")).full_name == full_name
    assert UserProfileUpdateIn(full_name=full_name).full_name == full_name

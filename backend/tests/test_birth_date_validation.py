from datetime import date, timedelta

import pytest
from pydantic import ValidationError

from app.schemas import ProfileIn, UserProfileUpdateIn


def _profile_data(birth_date: date) -> dict:
    return {
        "gender": "MALE",
        "birth_date": birth_date,
        "height_cm": 170,
        "weight_kg": 65,
        "activity_level": 3,
        "goal": "MAINTAIN",
    }


@pytest.mark.parametrize(
    "birth_date",
    [date.today() + timedelta(days=1), date.today().replace(year=date.today().year - 121)],
)
def test_register_rejects_illogical_birth_date(birth_date: date):
    with pytest.raises(ValidationError):
        ProfileIn(**_profile_data(birth_date))


@pytest.mark.parametrize(
    "birth_date",
    [date.today() + timedelta(days=1), date.today().replace(year=date.today().year - 121)],
)
def test_profile_update_rejects_illogical_birth_date(birth_date: date):
    with pytest.raises(ValidationError):
        UserProfileUpdateIn(birth_date=birth_date)


def test_birth_date_accepts_boundary_values():
    today = date.today()
    oldest = today.replace(year=today.year - 120)

    assert ProfileIn(**_profile_data(today)).birth_date == today
    assert UserProfileUpdateIn(birth_date=oldest).birth_date == oldest

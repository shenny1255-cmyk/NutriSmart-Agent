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
    [
        date.today() + timedelta(days=1),                     # Trong tương lai
        date.today(),                                          # 0 tuổi (< 15)
        date.today().replace(year=date.today().year - 14),     # 14 tuổi (< 15)
        date.today().replace(year=date.today().year - 101),    # 101 tuổi (> 100)
        date(1919, 12, 31),                                    # Trước năm 1920
    ],
)
def test_register_rejects_illogical_birth_date(birth_date: date):
    with pytest.raises(ValidationError):
        ProfileIn(**_profile_data(birth_date))


@pytest.mark.parametrize(
    "birth_date",
    [
        date.today() + timedelta(days=1),
        date.today(),
        date.today().replace(year=date.today().year - 14),
        date.today().replace(year=date.today().year - 101),
        date(1919, 12, 31),
    ],
)
def test_profile_update_rejects_illogical_birth_date(birth_date: date):
    with pytest.raises(ValidationError):
        UserProfileUpdateIn(birth_date=birth_date)


def test_birth_date_accepts_boundary_values():
    today = date.today()
    age_15 = today.replace(year=today.year - 15)
    age_100 = today.replace(year=today.year - 100)

    assert ProfileIn(**_profile_data(age_15)).birth_date == age_15
    assert UserProfileUpdateIn(birth_date=age_100).birth_date == age_100


def test_birth_date_error_messages():
    today = date.today()
    # Tương lai
    with pytest.raises(ValidationError) as exc_future:
        ProfileIn(**_profile_data(today + timedelta(days=1)))
    assert "Ngày sinh không được ở trong tương lai" in str(exc_future.value)

    # Dưới 15 tuổi
    with pytest.raises(ValidationError) as exc_young:
        ProfileIn(**_profile_data(today.replace(year=today.year - 14)))
    assert "Người dùng phải từ 15 tuổi trở lên" in str(exc_young.value)

    # Quá 100 tuổi
    with pytest.raises(ValidationError) as exc_old:
        ProfileIn(**_profile_data(today.replace(year=today.year - 101)))
    assert "Tuổi không được vượt quá 100" in str(exc_old.value)

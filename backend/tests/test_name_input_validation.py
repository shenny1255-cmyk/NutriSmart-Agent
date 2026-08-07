import pytest
from pydantic import ValidationError

from app.schemas import MealLogIn


@pytest.mark.parametrize("name", ["Phở 🍜", "Món ăn @@@", "🥗🥗"])
def test_luu_mon_tu_phan_tich_khong_nhan_emoji_hoac_ky_tu_dac_biet(name):
    with pytest.raises(ValidationError):
        MealLogIn(food_name=name, calories_kcal=100)


def test_luu_mon_tu_phan_tich_nhan_ten_hop_le():
    payload = MealLogIn(food_name="Phở bò tái", calories_kcal=480)
    assert payload.food_name == "Phở bò tái"

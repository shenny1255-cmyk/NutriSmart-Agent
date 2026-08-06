import pytest
from pydantic import ValidationError

from app.schemas import ManualMealIn


@pytest.mark.parametrize("food_name", ["A", "@@@", "Cơm 😊", "Món###123"])
def test_rejects_illogical_food_name(food_name: str):
    with pytest.raises(ValidationError):
        ManualMealIn(food_name=food_name, calories_kcal=500)


@pytest.mark.parametrize("food_name", ["Phở bò", "Sữa chua 0%", "Cơm gà (1/2 phần)", "Bún chả - nem"])
def test_accepts_valid_food_name(food_name: str):
    assert ManualMealIn(food_name=food_name, calories_kcal=500).food_name == food_name


@pytest.mark.parametrize("calories_kcal", [0, 5000.1])
def test_rejects_calories_outside_logical_range(calories_kcal: float):
    with pytest.raises(ValidationError):
        ManualMealIn(food_name="Phở bò", calories_kcal=calories_kcal)


@pytest.mark.parametrize("quantity", [0.49, 20.1])
def test_rejects_illogical_meal_quantity(quantity: float):
    with pytest.raises(ValidationError):
        ManualMealIn(food_name="Phở bò", calories_kcal=500, quantity=quantity)


def test_accepts_manual_meal_boundary_values():
    assert ManualMealIn(food_name="Phở bò", calories_kcal=1, quantity=0.5)
    assert ManualMealIn(food_name="Phở bò", calories_kcal=5000, quantity=20)

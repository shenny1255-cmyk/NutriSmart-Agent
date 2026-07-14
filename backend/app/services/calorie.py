from datetime import date


ACTIVITY_FACTOR = {
    1: 1.2,    # ít vận động
    2: 1.375,  # nhẹ
    3: 1.55,   # vừa
    4: 1.725,  # nhiều
    5: 1.9,    # rất nhiều
}

GOAL_ADJUST = {
    "LOSE_WEIGHT": -500,   # thâm hụt ~0.5kg/tuần
    "MAINTAIN":       0,
    "GAIN_MUSCLE":  300,
    "MEDICAL":        0,   # cần chuyên gia can thiệp
}


def calc_age(birth_date: date) -> int:
    today = date.today()
    return today.year - birth_date.year - (
        (today.month, today.day) < (birth_date.month, birth_date.day)
    )


def daily_calorie_target(
    gender: str, birth_date: date, height_cm: float,
    weight_kg: float, activity_level: int, goal: str,
) -> int:
    age = calc_age(birth_date)

    # BMR — Mifflin-St Jeor
    bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age
    bmr += 5 if gender == "MALE" else -161

    # TDEE
    tdee = bmr * ACTIVITY_FACTOR.get(activity_level, 1.55)

    target = tdee + GOAL_ADJUST.get(goal, 0)

    # Sàn an toàn — không để lộ trình gợi ý mức nguy hiểm
    floor = 1500 if gender == "MALE" else 1200
    return int(max(target, floor))
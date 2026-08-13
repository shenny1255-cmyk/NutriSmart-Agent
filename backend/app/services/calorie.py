from datetime import date


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


def calories_burned(met: float | None, weight_kg: float | None, minutes: int | None) -> float:
    """Calo tiêu hao của một buổi tập: MET × 3.5 × cân nặng / 200 × số phút.

    Thiếu bất kỳ dữ liệu nào (bài tập chưa có MET, hồ sơ chưa có cân nặng) → 0,
    lúc đó người dùng tự nhập số calo.
    """
    if not met or not weight_kg or not minutes:
        return 0.0
    return round(float(met) * 3.5 * float(weight_kg) / 200 * int(minutes), 2)


def manual_calories_limit(
    met: float | None,
    weight_kg: float | None,
    minutes: int,
) -> tuple[float, float]:
    """Trả kcal dự kiến và trần rộng để kiểm tra số liệu nhập từ thiết bị.

    Trần cho phép sai số lớn so với công thức MET nhưng không vượt quá 30 kcal/phút.
    Khi thiếu cân nặng, giới hạn theo thời gian vẫn ngăn các giá trị phi thực tế rõ ràng.
    """
    expected = calories_burned(met, weight_kg, minutes)
    time_limit = float(minutes * 30)
    if expected <= 0:
        return expected, time_limit
    return expected, min(expected * 3 + 10, time_limit)


def daily_calorie_target(
    gender: str, birth_date: date, height_cm: float,
    weight_kg: float, activity_multiplier: float, goal: str,
) -> int:
    age = calc_age(birth_date)

    # BMR — Mifflin-St Jeor
    bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age
    bmr += 5 if gender == "MALE" else -161

    # TDEE
    tdee = bmr * activity_multiplier

    target = tdee + GOAL_ADJUST.get(goal, 0)

    # Sàn an toàn — không để lộ trình gợi ý mức nguy hiểm
    floor = 1500 if gender == "MALE" else 1200
    return int(max(target, floor))

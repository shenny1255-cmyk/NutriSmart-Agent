"""Unit tests cho render_system_prompt — hàm thuần, không chạm database."""

from app.services.nutrition_context import render_system_prompt


FULL_CTX = {
    "full_name": "Nam",
    "profile": {
        "gender": "MALE",
        "age": 28,
        "height_cm": 175,
        "weight_kg": 72,
        "bmi": 23.5,
        "goal": "LOSE_WEIGHT",
        "daily_calorie_target": 1800,
        "conditions": ["Tiểu đường type 2"],
        "allergens": ["đậu phộng"],
    },
    "active_plan": {"version": 2, "daily_kcal_target": 1800},
    "tracking": {"days": 7, "avg_intake": 1950.0, "avg_burned": 300.0},
}


def test_always_includes_safety_and_identity():
    prompt = render_system_prompt({"full_name": None, "profile": None,
                                   "active_plan": None, "tracking": None})
    assert "NutriSmart" in prompt
    # Phải nêu rõ không phải bác sĩ
    assert "bác sĩ" in prompt.lower()


def test_full_context_includes_profile_details():
    prompt = render_system_prompt(FULL_CTX)
    assert "LOSE_WEIGHT" in prompt
    assert "1800" in prompt
    assert "đậu phộng" in prompt            # dị ứng
    assert "Tiểu đường type 2" in prompt     # bệnh nền


def test_full_context_includes_plan_and_tracking():
    prompt = render_system_prompt(FULL_CTX)
    assert "2" in prompt                     # phiên bản lộ trình
    assert "1950" in prompt                   # trung bình nạp
    assert "300" in prompt                    # trung bình tiêu hao


def test_missing_profile_nudges_user_and_does_not_crash():
    ctx = {"full_name": "An", "profile": None, "active_plan": None, "tracking": None}
    prompt = render_system_prompt(ctx)
    # Gợi ý người dùng hoàn thiện hồ sơ
    assert "hồ sơ" in prompt.lower()


def test_missing_plan_omits_plan_line():
    ctx = {**FULL_CTX, "active_plan": None}
    prompt = render_system_prompt(ctx)
    assert "Lộ trình" not in prompt


def test_missing_tracking_omits_tracking_line():
    ctx = {**FULL_CTX, "tracking": None}
    prompt = render_system_prompt(ctx)
    assert "Theo dõi" not in prompt

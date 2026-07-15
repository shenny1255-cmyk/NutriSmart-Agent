"""Xây dựng system prompt cho Trợ lý AI, dựa trên dữ liệu sức khỏe của người dùng.

Tách làm 2 phần để dễ kiểm thử:
- render_system_prompt(ctx)  -> hàm THUẦN, không chạm DB (unit test).
- build_system_prompt(db, user) -> lấy dữ liệu từ DB rồi gọi render (integration).
"""

from datetime import date, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models import (
    User, MedicalCondition, Allergen,
    ProfileCondition, ProfileAllergen, NutritionPlan,
)
from app.services.calorie import calc_age

_SAFETY = (
    "Bạn là trợ lý dinh dưỡng của ứng dụng NutriSmart. Trả lời bằng tiếng Việt, "
    "ngắn gọn và thực tế. Bạn KHÔNG phải bác sĩ: với mục tiêu y tế (MEDICAL) hoặc "
    "bệnh nền nghiêm trọng, hãy khuyên người dùng tham khảo ý kiến chuyên gia y tế."
)


def render_system_prompt(ctx: dict) -> str:
    """Ghép các mảnh dữ liệu thành system prompt. Bỏ qua phần nào thiếu dữ liệu."""
    lines = [_SAFETY, ""]

    name = ctx.get("full_name")
    if name:
        lines.append(f"Bạn đang trò chuyện với {name}.")

    profile = ctx.get("profile")
    if profile:
        conditions = ", ".join(profile.get("conditions") or []) or "không có"
        allergens = ", ".join(profile.get("allergens") or []) or "không có"
        lines.append("Hồ sơ người dùng:")
        lines.append(
            f"- Mục tiêu: {profile['goal']} · "
            f"Mục tiêu calo: {profile['daily_calorie_target']} kcal/ngày"
        )
        lines.append(
            f"- Giới tính: {profile['gender']} · Tuổi: {profile['age']} · "
            f"Cao {profile['height_cm']}cm · Nặng {profile['weight_kg']}kg · "
            f"BMI {profile['bmi']}"
        )
        lines.append(f"- Bệnh nền: {conditions} · Dị ứng: {allergens}")
    else:
        lines.append(
            "Người dùng chưa hoàn thiện hồ sơ sức khỏe. Hãy trả lời chung chung và "
            "gợi ý họ cập nhật hồ sơ để nhận tư vấn cá nhân hóa hơn."
        )

    plan = ctx.get("active_plan")
    if plan:
        lines.append(
            f"Lộ trình đang áp dụng: phiên bản {plan['version']}, "
            f"{plan['daily_kcal_target']} kcal/ngày."
        )

    tracking = ctx.get("tracking")
    if tracking:
        lines.append(
            f"Theo dõi {tracking['days']} ngày gần đây: trung bình nạp "
            f"{tracking['avg_intake']:.0f} kcal, tiêu hao {tracking['avg_burned']:.0f} "
            "kcal mỗi ngày."
        )

    return "\n".join(lines)


def gather_context(db: Session, user: User, tracking_days: int = 7) -> dict:
    """Truy vấn hồ sơ + lộ trình + theo dõi từ DB, trả về ctx cho render_system_prompt."""
    ctx: dict = {"full_name": user.full_name, "profile": None,
                 "active_plan": None, "tracking": None}

    profile = user.profile
    if profile:
        conditions = (
            db.query(MedicalCondition.name)
            .join(ProfileCondition, ProfileCondition.condition_id == MedicalCondition.id)
            .filter(ProfileCondition.profile_id == profile.id).all()
        )
        allergens = (
            db.query(Allergen.name)
            .join(ProfileAllergen, ProfileAllergen.allergen_id == Allergen.id)
            .filter(ProfileAllergen.profile_id == profile.id).all()
        )
        ctx["profile"] = {
            "gender": profile.gender,
            "age": calc_age(profile.birth_date) if profile.birth_date else "?",
            "height_cm": profile.height_cm,
            "weight_kg": profile.weight_kg,
            "bmi": profile.bmi,
            "goal": profile.goal,
            "daily_calorie_target": profile.daily_calorie_target,
            "conditions": [c[0] for c in conditions],
            "allergens": [a[0] for a in allergens],
        }

    plan = (
        db.query(NutritionPlan)
        .filter(NutritionPlan.user_id == user.id, NutritionPlan.status == "ACTIVE")
        .order_by(NutritionPlan.version.desc()).first()
    )
    if plan:
        ctx["active_plan"] = {"version": plan.version,
                              "daily_kcal_target": plan.daily_kcal_target}

    since = date.today() - timedelta(days=tracking_days - 1)
    row = db.execute(
        text("""
            SELECT AVG(kcal_intake) AS intake, AVG(kcal_burned) AS burned, COUNT(*) AS n
            FROM v_daily_summary WHERE user_id = :uid AND day >= :since
        """),
        {"uid": str(user.id), "since": since},
    ).mappings().first()
    if row and row["n"]:
        ctx["tracking"] = {"days": tracking_days,
                           "avg_intake": float(row["intake"] or 0),
                           "avg_burned": float(row["burned"] or 0)}

    return ctx


def build_system_prompt(db: Session, user: User) -> str:
    return render_system_prompt(gather_context(db, user))

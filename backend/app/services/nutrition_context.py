from sqlalchemy.orm import Session
from app.models import User


_SAFETY = (
    "Bạn là trợ lý dinh dưỡng NutriSmart Agent, tư vấn sức khỏe và dinh dưỡng cá nhân hóa. "
    "Bạn không phải bác sĩ hay chuyên gia y tế, không thay thế chẩn đoán hay điều trị y khoa. "
    "Bạn trả lời bằng tiếng Việt, lịch sự, ngắn gọn và có căn cứ khoa học."
)


def render_system_prompt(ctx: dict) -> str:
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
    full_name = user.info.full_name if user.info else "Người dùng"

    ctx: dict = {
        "full_name": full_name,
        "profile": None,
        "active_plan": None,
        "tracking": None,
    }

    if user.info:
        info = user.info
        from datetime import date
        age = (date.today() - info.birth_date).days // 365 if info.birth_date else None
        conditions = [c.name for c in getattr(info, "conditions", [])]
        allergens = [a.name for a in getattr(info, "allergens", [])]
        conditions.extend(getattr(info, "custom_conditions", []) or [])
        allergens.extend(
            item.get("name", "") if isinstance(item, dict) else str(item)
            for item in (getattr(info, "custom_allergens", []) or [])
        )
        ctx["profile"] = {
            "goal": info.goal,
            "gender": info.gender,
            "age": age,
            "height_cm": info.height_cm,
            "weight_kg": info.weight_kg,
            "bmi": info.bmi,
            "daily_calorie_target": info.daily_calorie_target,
            "conditions": conditions,
            "allergens": allergens,
        }

    try:
        from app.models import NutritionPlan
        plan = (
            db.query(NutritionPlan)
            .filter(NutritionPlan.user_id == user.id)
            .order_by(NutritionPlan.version.desc())
            .first()
        )
        if plan:
            ctx["active_plan"] = {
                "version": plan.version,
                "daily_kcal_target": plan.daily_kcal_target,
            }
    except Exception:
        pass

    return ctx


def build_system_prompt(db: Session, user: User) -> str:
    ctx = gather_context(db, user)
    return render_system_prompt(ctx)

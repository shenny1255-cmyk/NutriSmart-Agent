from datetime import date, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import ActivityLog, MealLog, User
from app.services.body_metrics import latest_body_metric


_SAFETY = (
    "Bạn là trợ lý dinh dưỡng NutriSmart Agent, tư vấn sức khỏe và dinh dưỡng cá nhân hóa. "
    "Bạn không phải bác sĩ hay chuyên gia y tế, không thay thế chẩn đoán hay điều trị y khoa. "
    "Bạn trả lời bằng tiếng Việt, lịch sự, ngắn gọn và có căn cứ khoa học."
)


# Ràng buộc cứng (UAT ISS-03): ép trả lời định lượng được, cấm lời khuyên sáo rỗng.
_CONSTRAINTS = (
    "QUY TẮC TRẢ LỜI BẮT BUỘC:\n"
    "1. Khi người dùng hỏi về ăn uống, thực đơn, giảm cân hoặc tăng cân: luôn đề xuất món ăn hoặc thực đơn "
    "cụ thể, ưu tiên món Việt Nam, kèm định lượng ước tính (gam, chén, đĩa, ml) và số kcal ước tính của từng món.\n"
    "2. Tổng năng lượng các bữa đề xuất phải bám sát mức calo mục tiêu hằng ngày của người dùng; nói rõ phần "
    "đề xuất chiếm khoảng bao nhiêu kcal so với mục tiêu đó.\n"
    "3. Cấm tuyệt đối các câu sáo rỗng, lý thuyết chung chung không thể định lượng được như \"hãy sống lành mạnh\", "
    "\"ăn uống điều độ\", \"ăn uống cân bằng\", \"tập thể dục đều đặn\". Mỗi lời khuyên phải quy đổi thành "
    "hành động cụ thể: ăn món gì, bao nhiêu, vào lúc nào, tập bài gì trong bao nhiêu phút.\n"
    "4. Quy tắc an toàn luôn được ưu tiên hơn các quy tắc trên: không dùng thực phẩm người dùng bị dị ứng, "
    "chọn món phù hợp bệnh nền, khuyên đi khám khi có dấu hiệu bất thường.\n"
    "5. PHẠM VI: chỉ trả lời về dinh dưỡng, ăn uống, vận động, sức khỏe và cách dùng NutriSmart. Câu hỏi "
    "ngoài phạm vi (sửa xe, lập trình, thời sự, giải trí...) thì KHÔNG trả lời nội dung đó: chỉ nói ngắn gọn "
    "trong 1-2 câu rằng câu hỏi nằm ngoài phạm vi hỗ trợ, rồi gợi ý một câu hỏi về dinh dưỡng."
)


GOAL_MAP = {
    "LOSE_WEIGHT": "Giảm cân",
    "MAINTAIN": "Duy trì cân nặng",
    "GAIN_WEIGHT": "Tăng cân",
}


def render_system_prompt(ctx: dict) -> str:
    lines = [_SAFETY, "", _CONSTRAINTS, ""]

    name = ctx.get("full_name")
    if name:
        lines.append(f"Bạn đang trò chuyện với {name}.")

    profile = ctx.get("profile")
    if profile:
        conditions = ", ".join(profile.get("conditions") or []) or "không có"
        allergens = ", ".join(profile.get("allergens") or []) or "không có"
        raw_goal = str(profile.get("goal") or "")
        goal_str = GOAL_MAP.get(raw_goal.upper(), raw_goal)
        lines.append("Hồ sơ người dùng:")
        lines.append(
            f"- Mục tiêu: {goal_str} · "
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
            "Người dùng chưa hoàn thiện hồ sơ sức khỏe. Khi đề xuất thực đơn, dùng mức tham chiếu "
            "2000 kcal/ngày, nói rõ đây là mức tham chiếu chung và gợi ý họ cập nhật hồ sơ để nhận "
            "tư vấn cá nhân hóa hơn."
        )

    plan = ctx.get("active_plan")
    if plan:
        lines.append(
            f"Lộ trình đang áp dụng: phiên bản {plan['version']}, "
            f"{plan['daily_kcal_target']} kcal/ngày."
        )

    tracking = ctx.get("tracking")
    if tracking:
        logged = tracking.get("logged_days")
        scope = f" (có ghi bữa ăn {logged}/{tracking['days']} ngày)" if logged else ""
        lines.append(
            f"Theo dõi {tracking['days']} ngày gần đây{scope}: trung bình nạp "
            f"{tracking['avg_intake']:.0f} kcal, tiêu hao {tracking['avg_burned']:.0f} "
            "kcal mỗi ngày."
        )

    return "\n".join(lines)


def _ngay_viet_nam(column):
    """Đổi TIMESTAMPTZ sang ngày Việt Nam, giống cách trang Nhật ký lọc vận động theo ngày."""
    return func.date(func.timezone("Asia/Bangkok", column))


def tracking_summary(db: Session, user_id, days: int = 7) -> dict | None:
    """Calo nạp và tiêu hao trung bình trong `days` ngày gần nhất, tính cả hôm nay (UAT ISS-01).

    Chia theo số ngày CÓ ghi nhật ký, không chia cho cả `days`: người dùng quên ghi 4/7 ngày thì
    chia 7 sẽ ra mức ăn thiếu giả. Tiêu hao chỉ gồm vận động đã ghi, không phải tổng TDEE.
    Chưa có bữa ăn nào trong khoảng này thì trả None vì không đánh giá được lượng nạp.
    """
    since = date.today() - timedelta(days=days - 1)
    meals = dict(
        db.query(MealLog.log_date, func.sum(MealLog.calories_kcal))
        .filter(MealLog.user_id == user_id, MealLog.log_date >= since)  # type: ignore
        .group_by(MealLog.log_date)
        .all()
    )
    if not meals:
        return None
    activity_day = _ngay_viet_nam(func.coalesce(ActivityLog.started_at, ActivityLog.logged_at))
    burned = dict(
        db.query(activity_day, func.sum(ActivityLog.calories_burned))
        .filter(ActivityLog.user_id == user_id, activity_day >= since)  # type: ignore
        .group_by(activity_day)
        .all()
    )
    tracked_days = len(set(meals) | set(burned))
    return {
        "days": days,
        "logged_days": len(meals),
        "avg_intake": round(sum(float(v or 0) for v in meals.values()) / len(meals), 1),
        "avg_burned": round(sum(float(v or 0) for v in burned.values()) / tracked_days, 1),
    }


def gather_context(db: Session, user: User, tracking_days: int = 7) -> dict:
    full_name = user.profile.full_name if user.profile else "Người dùng"

    ctx: dict = {
        "full_name": full_name,
        "profile": None,
        "active_plan": None,
        "tracking": None,
    }

    if user.profile:
        info = user.profile
        metric = latest_body_metric(db, user.id)
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
            "height_cm": metric.height_cm if metric else None,
            "weight_kg": metric.weight_kg if metric else None,
            "bmi": metric.bmi if metric else None,
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

    ctx["tracking"] = tracking_summary(db, user.id, tracking_days)
    return ctx


def build_system_prompt(db: Session, user: User) -> str:
    ctx = gather_context(db, user)
    return render_system_prompt(ctx)

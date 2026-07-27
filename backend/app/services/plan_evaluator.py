"""Job đánh giá lộ trình sau mỗi chu kỳ 7 ngày (task 12).

Luồng: lộ trình ACTIVE đủ 7 ngày → tính calo trung bình nạp vào + biến thiên cân nặng
→ kết luận ĐẠT / ĐẠT MỘT PHẦN / KHÔNG ĐẠT → ghi plan_evaluations → sinh lộ trình
version+1 (calo đã hiệu chỉnh) và hạ lộ trình cũ xuống REVISED (hoặc COMPLETED nếu ĐẠT).
"""
import logging
from datetime import date, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models import User, NutritionPlan, PlanEvaluation
from app.services import ollama_client, plan_generator

logger = logging.getLogger(__name__)

PERIOD_DAYS = 7          # một chu kỳ đánh giá
KCAL_TOLERANCE = 0.10    # lệch calo trong ±10% coi là tuân thủ tốt
KCAL_STEP = 0.10         # mức hiệu chỉnh calo cho phiên bản kế tiếp
MIN_KCAL = 1200          # ngưỡng an toàn, không hạ thấp hơn
MAX_KCAL = 4000

# Kỳ vọng biến thiên cân nặng sau 7 ngày theo từng mục tiêu
WEIGHT_RULES = {
    "LOSE_WEIGHT": lambda d: d <= -0.3,
    "GAIN_MUSCLE": lambda d: d >= 0.2,
    "MAINTAIN":    lambda d: abs(d) <= 0.7,
    "MEDICAL":     lambda d: abs(d) <= 0.7,
}

RESULT_LABELS = {
    "ACHIEVED":     "ĐẠT",
    "PARTIAL":      "ĐẠT MỘT PHẦN",
    "NOT_ACHIEVED": "KHÔNG ĐẠT",
}


# ---------- Logic thuần (không đụng DB → dễ test) ----------

def is_due(start_date: date, today: date | None = None) -> bool:
    """Lộ trình đã chạy đủ PERIOD_DAYS ngày chưa?"""
    today = today or date.today()
    return (today - start_date).days >= PERIOD_DAYS


def kcal_ok(avg_kcal_intake: float | None, target: int) -> bool:
    """Calo trung bình nạp vào có nằm trong ±KCAL_TOLERANCE quanh mục tiêu không."""
    if avg_kcal_intake is None or not target:
        return False
    return abs(avg_kcal_intake - target) / target <= KCAL_TOLERANCE


def weight_ok(goal: str, weight_change_kg: float | None) -> bool | None:
    """True/False theo kỳ vọng của mục tiêu; None khi chưa có dữ liệu cân nặng."""
    if weight_change_kg is None:
        return None
    rule = WEIGHT_RULES.get(goal, WEIGHT_RULES["MAINTAIN"])
    return rule(float(weight_change_kg))


def decide_result(
    avg_kcal_intake: float | None,
    target: int,
    goal: str,
    weight_change_kg: float | None,
) -> str:
    """ACHIEVED khi đạt cả 2 tiêu chí, PARTIAL khi đạt 1, còn lại NOT_ACHIEVED.

    Thiếu dữ liệu cân nặng thì cao nhất chỉ được PARTIAL — chưa đủ căn cứ kết luận ĐẠT.
    """
    ok_kcal = kcal_ok(avg_kcal_intake, target)
    ok_weight = weight_ok(goal, weight_change_kg)

    if ok_weight is None:
        return "PARTIAL" if ok_kcal else "NOT_ACHIEVED"
    if ok_kcal and ok_weight:
        return "ACHIEVED"
    if ok_kcal or ok_weight:
        return "PARTIAL"
    return "NOT_ACHIEVED"


def next_kcal_target(
    current_target: int,
    result: str,
    goal: str,
    weight_change_kg: float | None,
) -> int:
    """Hiệu chỉnh calo cho lộ trình kế tiếp — chỉ đổi khi kỳ vừa rồi chưa ĐẠT."""
    if result == "ACHIEVED":
        return current_target

    # Thiếu dữ liệu cân nặng (None) cũng coi như chưa đạt kỳ vọng → vẫn hiệu chỉnh
    chua_dung_huong = weight_ok(goal, weight_change_kg) is not True

    delta = 0
    if goal == "LOSE_WEIGHT" and chua_dung_huong:
        delta = -round(current_target * KCAL_STEP)
    elif goal == "GAIN_MUSCLE" and chua_dung_huong:
        delta = round(current_target * KCAL_STEP)

    return max(MIN_KCAL, min(MAX_KCAL, current_target + delta))


def build_note(result: str, target: int, new_target: int, avg_kcal: float | None,
               weight_change_kg: float | None) -> str:
    """Ghi chú nhét vào prompt sinh lộ trình mới."""
    parts = [f"Kỳ 7 ngày vừa rồi: {RESULT_LABELS[result]}."]
    if avg_kcal is not None:
        parts.append(f"Calo trung bình thực tế {avg_kcal:.0f} kcal/ngày so với mục tiêu {target} kcal.")
    else:
        parts.append("Người dùng ghi nhật ký ăn uống rất ít.")
    if weight_change_kg is not None:
        parts.append(f"Cân nặng thay đổi {weight_change_kg:+.1f} kg.")
    if new_target != target:
        huong = "giảm" if new_target < target else "tăng"
        parts.append(f"Lộ trình mới {huong} mục tiêu còn {new_target} kcal/ngày; "
                     "chia khẩu phần dễ theo hơn và tăng món no lâu.")
    else:
        parts.append("Giữ mức calo cũ nhưng phải đổi mới thực đơn so với tuần trước.")
    return " ".join(parts)


# ---------- Truy vấn số liệu ----------

def compute_metrics(db: Session, user_id, period_start: date, period_end: date) -> tuple[float | None, float | None]:
    """(calo trung bình nạp vào/ngày, biến thiên cân nặng kg) trong khoảng đánh giá."""
    avg_row = db.execute(text("""
        SELECT SUM(calories_kcal) AS total, COUNT(DISTINCT log_date) AS ngay
        FROM meal_logs
        WHERE user_id = :uid AND log_date BETWEEN :s AND :e
    """), {"uid": str(user_id), "s": period_start, "e": period_end}).mappings().first()

    avg_kcal = None
    if avg_row and avg_row["ngay"]:
        # Chia cho trọn chu kỳ: ngày không ghi nhật ký vẫn tính là ăn ít
        avg_kcal = float(avg_row["total"] or 0) / PERIOD_DAYS

    w_row = db.execute(text("""
        SELECT
            (SELECT weight_kg FROM body_metrics_history
              WHERE user_id = :uid AND recorded_at <= :s
              ORDER BY recorded_at DESC LIMIT 1) AS dau_ky,
            (SELECT weight_kg FROM body_metrics_history
              WHERE user_id = :uid AND recorded_at <= :e
              ORDER BY recorded_at DESC LIMIT 1) AS cuoi_ky
    """), {"uid": str(user_id), "s": period_start, "e": period_end}).mappings().first()

    weight_change = None
    if w_row and w_row["dau_ky"] is not None and w_row["cuoi_ky"] is not None:
        weight_change = float(w_row["cuoi_ky"]) - float(w_row["dau_ky"])

    return avg_kcal, weight_change


def _llm_feedback(profile_ctx: dict, result: str, target: int, avg_kcal: float | None,
                  weight_change_kg: float | None) -> str:
    """Nhận xét ngắn bằng tiếng Việt; rơi về câu mẫu khi Ollama lỗi."""
    prompt = f"""Bạn là chuyên gia dinh dưỡng. Hãy viết nhận xét NGẮN (tối đa 3 câu, tiếng Việt)
cho người dùng sau khi kết thúc 7 ngày áp dụng lộ trình:
- Mục tiêu: {profile_ctx.get('goal')}
- Bệnh nền: {', '.join(profile_ctx.get('conditions') or []) or 'không có'}
- Calo mục tiêu: {target} kcal/ngày
- Calo trung bình thực tế: {f'{avg_kcal:.0f} kcal/ngày' if avg_kcal is not None else 'không đủ dữ liệu'}
- Biến thiên cân nặng: {f'{weight_change_kg:+.1f} kg' if weight_change_kg is not None else 'chưa cập nhật'}
- Kết luận của hệ thống: {RESULT_LABELS[result]}
Nêu 1 điểm làm tốt và 1 việc cần chỉnh cho tuần tới. Không dùng markdown."""
    try:
        return ollama_client.chat(
            [{"role": "user", "content": prompt}],
            timeout=120.0,
            options={"num_predict": 220},
        )
    except Exception as e:
        logger.warning("Không sinh được nhận xét AI: %s", e)
        return (
            f"Kết quả 7 ngày: {RESULT_LABELS[result]}. "
            "Hãy ghi nhật ký ăn uống đều đặn và cập nhật cân nặng để hệ thống "
            "hiệu chỉnh lộ trình chính xác hơn."
        )


# ---------- Job ----------

def active_plan(db: Session, user: User) -> NutritionPlan | None:
    return (
        db.query(NutritionPlan)
        .filter(NutritionPlan.user_id == user.id, NutritionPlan.status == "ACTIVE")  # type: ignore
        .order_by(NutritionPlan.version.desc())
        .first()
    )


def already_evaluated(db: Session, plan_id, period_start: date) -> bool:
    return (
        db.query(PlanEvaluation)
        .filter(PlanEvaluation.plan_id == plan_id,
                PlanEvaluation.period_start == period_start)  # type: ignore
        .first()
        is not None
    )


def run_plan_job(db: Session, user: User, force: bool = False) -> dict:
    """Chấm lộ trình đang chạy của một user và sinh phiên bản kế tiếp nếu đến hạn.

    force=True dùng cho demo/nút bấm tay: chấm luôn dù chưa đủ 7 ngày.
    Trả về {"evaluated": bool, "reason": str|None, "evaluation": ..., "plan": ...}.
    """
    plan = active_plan(db, user)
    if not plan:
        return {"evaluated": False, "reason": "Chưa có lộ trình nào đang áp dụng"}

    if not force and not is_due(plan.start_date):
        con_lai = PERIOD_DAYS - (date.today() - plan.start_date).days
        return {"evaluated": False, "reason": f"Lộ trình chưa đủ 7 ngày (còn {con_lai} ngày)"}

    period_start = plan.start_date
    period_end = min(date.today(), period_start + timedelta(days=PERIOD_DAYS - 1))

    if already_evaluated(db, plan.id, period_start):
        return {"evaluated": False, "reason": "Kỳ này đã được đánh giá"}

    target = plan.daily_kcal_target or 2000
    goal = plan.goal or "MAINTAIN"

    avg_kcal, weight_change = compute_metrics(db, user.id, period_start, period_end)
    result = decide_result(avg_kcal, target, goal, weight_change)
    new_target = next_kcal_target(target, result, goal, weight_change)

    from app.services.nutrition_context import gather_context
    profile_ctx = (gather_context(db, user).get("profile")) or {"goal": goal}
    feedback = _llm_feedback(profile_ctx, result, target, avg_kcal, weight_change)

    evaluation = PlanEvaluation(
        plan_id=plan.id,
        period_start=period_start,
        period_end=period_end,
        avg_kcal_intake=round(avg_kcal, 2) if avg_kcal is not None else None,
        weight_change_kg=round(weight_change, 2) if weight_change is not None else None,
        result=result,
        ai_feedback=feedback,
    )
    db.add(evaluation)

    # Đồng bộ mục tiêu calo mới vào hồ sơ để dashboard/chat dùng chung một con số
    if user.profile and new_target != target:
        user.profile.daily_calorie_target = new_target

    note = build_note(result, target, new_target, avg_kcal, weight_change)
    new_plan = plan_generator.create_plan(
        db, user,
        target=new_target,
        note=note,
        # ĐẠT → coi như hoàn thành; chưa đạt → lộ trình cũ bị hiệu chỉnh
        old_status="COMPLETED" if result == "ACHIEVED" else "REVISED",
    )

    db.commit()
    db.refresh(evaluation)
    db.refresh(new_plan)

    logger.info("Đánh giá lộ trình %s của %s: %s → sinh version %s",
                plan.version, user.email, result, new_plan.version)

    return {
        "evaluated": True,
        "reason": None,
        "evaluation": evaluation,
        "plan": new_plan,
    }


def run_job_for_all(db: Session) -> dict:
    """Quét toàn bộ user có lộ trình ACTIVE đã đủ 7 ngày. Dùng cho job nền / admin."""
    han = date.today() - timedelta(days=PERIOD_DAYS)
    users = (
        db.query(User)
        .join(NutritionPlan, NutritionPlan.user_id == User.id)  # type: ignore
        .filter(NutritionPlan.status == "ACTIVE",  # type: ignore
                NutritionPlan.start_date <= han,  # type: ignore
                User.deleted_at.is_(None),
                User.is_active.is_(True))
        .distinct()
        .all()
    )

    da_danh_gia, bo_qua, loi = 0, 0, 0
    for u in users:
        try:
            if run_plan_job(db, u)["evaluated"]:
                da_danh_gia += 1
            else:
                bo_qua += 1
        except Exception as e:
            db.rollback()
            loi += 1
            logger.error("Lỗi đánh giá lộ trình của %s: %s", u.email, e, exc_info=True)

    return {"tong_user": len(users), "da_danh_gia": da_danh_gia, "bo_qua": bo_qua, "loi": loi}


async def scheduler_loop():
    """Job nền: cứ PLAN_EVAL_INTERVAL_MINUTES phút lại quét các lộ trình đã đủ 7 ngày.

    DB session là đồng bộ nên phần nặng được đẩy sang threadpool để không chẹn event loop.
    """
    import asyncio
    from starlette.concurrency import run_in_threadpool

    from app.config import settings
    from app.database import SessionLocal

    await asyncio.sleep(settings.PLAN_EVAL_DELAY_SECONDS)
    while True:
        db = SessionLocal()
        try:
            ket_qua = await run_in_threadpool(run_job_for_all, db)
            if ket_qua["tong_user"]:
                logger.info("Job đánh giá lộ trình: %s", ket_qua)
        except Exception as e:
            logger.error("Job đánh giá lộ trình lỗi: %s", e, exc_info=True)
        finally:
            db.close()
        await asyncio.sleep(settings.PLAN_EVAL_INTERVAL_MINUTES * 60)


def evaluation_to_dict(e: PlanEvaluation) -> dict:
    return {
        "id": e.id,
        "plan_id": e.plan_id,
        "period_start": e.period_start,
        "period_end": e.period_end,
        "avg_kcal_intake": float(e.avg_kcal_intake) if e.avg_kcal_intake is not None else None,
        "weight_change_kg": float(e.weight_change_kg) if e.weight_change_kg is not None else None,
        "result": e.result,
        "result_label": RESULT_LABELS.get(e.result, e.result),
        "ai_feedback": e.ai_feedback,
        "evaluated_at": e.evaluated_at,
    }

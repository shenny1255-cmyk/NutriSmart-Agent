"""Nghiệp vụ check-in tiến độ 14 ngày.

Phần đánh giá dùng quy tắc xác định để luôn chạy được khi Ollama ngoại tuyến.
AI chỉ diễn giải kết quả đã được hệ thống tính sẵn.
"""
import asyncio
import logging
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.models import (
    NutritionPlan,
    PlanCheckin,
    PlanCheckinSeries,
    Notification,
    User,
)
from app.services.body_metrics import latest_body_metric, upsert_body_metric
from app.services import ollama_client


PERIOD_DAYS = 14
GRACE_DAYS = 3
MIN_MEAL_LOG_DAYS = 7
MIN_KCAL = 1200
MAX_KCAL = 4000
KCAL_STEP = 0.10
PREDICTION_RULE_VERSION = "weight-range-v1"

logger = logging.getLogger(__name__)

RECOMMENDATION_REASONS = {
    "NEEDS_REVIEW": (
        "Vui lòng kiểm tra lại số liệu. Nếu số liệu chính xác, bạn nên trao đổi với "
        "chuyên gia y tế trước khi thay đổi lộ trình."
    ),
    "CONTINUE_AND_TRACK": "Dữ liệu theo dõi chưa đủ để đánh giá chính xác; hãy tiếp tục ghi nhật ký.",
    "IMPROVE_ADHERENCE": "Mức tuân thủ chưa đủ cao để kết luận lộ trình không phù hợp.",
    "CONTINUE": "Tiến độ đang nằm trong khoảng kỳ vọng.",
    "CONTINUE_AND_MONITOR": "Tiến độ lệch kỳ vọng lần đầu; nên theo dõi thêm một kỳ trước khi điều chỉnh.",
    "ADJUST_PLAN": "Tiến độ lệch kỳ vọng hai kỳ liên tiếp dù mức tuân thủ cao.",
}


def display_status(status: str, due_date: date, grace_until: date, today: date | None = None) -> str:
    """Suy ra trạng thái hiển thị từ trạng thái bền vững và ngày hiện tại."""
    if status != "OPEN":
        return status
    today = today or date.today()
    if today < due_date:
        return "UPCOMING"
    if today <= grace_until:
        return "DUE"
    return "OVERDUE"


def expected_weight_range(baseline_weight_kg: float, goal: str) -> tuple[float, float]:
    """Tính khoảng kỳ vọng 14 ngày; các tỷ lệ phải được chuyên gia duyệt trước production."""
    weight = float(baseline_weight_kg)
    rates = {
        "LOSE_WEIGHT": (-0.02, -0.005),
        "GAIN_MUSCLE": (0.0025, 0.01),
        "MAINTAIN": (-0.01, 0.01),
        "MEDICAL": (-0.01, 0.01),
    }
    low_rate, high_rate = rates.get(goal, rates["MAINTAIN"])
    return round(weight * (1 + low_rate), 2), round(weight * (1 + high_rate), 2)


def derive_data_quality(has_weight: bool, meal_log_days: int) -> str:
    if not has_weight or meal_log_days <= 0:
        return "INSUFFICIENT"
    if meal_log_days < MIN_MEAL_LOG_DAYS:
        return "PARTIAL"
    return "SUFFICIENT"


def derive_adherence(adherence_pct: int) -> str:
    if adherence_pct >= 80:
        return "HIGH"
    if adherence_pct >= 50:
        return "MEDIUM"
    return "LOW"


def derive_outcome(
    actual_weight_kg: float,
    expected_min_kg: float,
    expected_max_kg: float,
    data_quality: str,
    adherence: str,
) -> str:
    if data_quality != "SUFFICIENT" or adherence != "HIGH":
        return "NOT_EVALUATED"
    if expected_min_kg <= actual_weight_kg <= expected_max_kg:
        return "WITHIN_EXPECTED_RANGE"
    return "BELOW_EXPECTED_RANGE" if actual_weight_kg < expected_min_kg else "ABOVE_EXPECTED_RANGE"


def derive_safety_flags(
    baseline_weight_kg: float,
    actual_weight_kg: float,
    energy_level: int,
    hunger_level: int,
    sleep_quality: int,
    goal: str,
) -> list[str]:
    flags: list[str] = []
    baseline = float(baseline_weight_kg)
    if baseline and abs(float(actual_weight_kg) - baseline) / baseline > 0.04:
        flags.append("RAPID_WEIGHT_CHANGE")
    if energy_level <= 1:
        flags.append("LOW_ENERGY")
    if hunger_level >= 5:
        flags.append("HIGH_HUNGER")
    if sleep_quality <= 1:
        flags.append("POOR_SLEEP")
    if goal == "MEDICAL":
        flags.append("MEDICAL_REVIEW")
    return flags


def derive_recommendation(
    data_quality: str,
    adherence: str,
    outcome: str,
    safety_flags: list[str],
    previous_off_track: bool,
    goal: str = "MAINTAIN",
) -> str:
    if safety_flags:
        return "NEEDS_REVIEW"
    if data_quality == "INSUFFICIENT":
        return "CONTINUE_AND_TRACK"
    if adherence in {"LOW", "MEDIUM"}:
        return "IMPROVE_ADHERENCE"
    if outcome == "WITHIN_EXPECTED_RANGE":
        return "CONTINUE"
    unfavorable = (
        (goal == "LOSE_WEIGHT" and outcome == "ABOVE_EXPECTED_RANGE")
        or (goal == "GAIN_MUSCLE" and outcome == "BELOW_EXPECTED_RANGE")
    )
    if unfavorable:
        return "ADJUST_PLAN" if previous_off_track else "CONTINUE_AND_MONITOR"
    if outcome in {"BELOW_EXPECTED_RANGE", "ABOVE_EXPECTED_RANGE"}:
        return "CONTINUE_AND_MONITOR"
    return "CONTINUE_AND_TRACK"


def propose_kcal_target(current_target: int, goal: str, recommendation: str) -> int | None:
    if recommendation != "ADJUST_PLAN" or goal == "MEDICAL":
        return None
    delta = 0
    if goal == "LOSE_WEIGHT":
        delta = -round(current_target * KCAL_STEP)
    elif goal == "GAIN_MUSCLE":
        delta = round(current_target * KCAL_STEP)
    return max(MIN_KCAL, min(MAX_KCAL, current_target + delta))


# ---------- Truy cập dữ liệu và vòng đời kỳ check-in ----------

def checkin_to_dict(checkin: PlanCheckin, today: date | None = None) -> dict:
    """Chuyển model sang response an toàn cho frontend."""
    return {
        "id": checkin.id,
        "plan_id": checkin.plan_id,
        "period_number": checkin.period_number,
        "start_date": checkin.start_date,
        "period_end": checkin.period_end,
        "due_date": checkin.due_date,
        "grace_until": checkin.grace_until,
        "display_status": display_status(checkin.status, checkin.due_date, checkin.grace_until, today),
        "status": checkin.status,
        "baseline_weight_kg": float(checkin.baseline_weight_kg),
        "expected_weight_min_kg": float(checkin.expected_weight_min_kg),
        "expected_weight_max_kg": float(checkin.expected_weight_max_kg),
        "target_kcal_snapshot": checkin.target_kcal_snapshot,
        "goal_snapshot": checkin.goal_snapshot,
        "actual_weight_kg": float(checkin.actual_weight_kg) if checkin.actual_weight_kg is not None else None,
        "actual_waist_cm": float(checkin.actual_waist_cm) if checkin.actual_waist_cm is not None else None,
        "actual_activity_level": checkin.actual_activity_level,
        "adherence_pct": checkin.adherence_pct,
        "energy_level": checkin.energy_level,
        "hunger_level": checkin.hunger_level,
        "sleep_quality": checkin.sleep_quality,
        "notes": checkin.notes,
        "meal_log_days": checkin.meal_log_days,
        "avg_kcal_intake": float(checkin.avg_kcal_intake) if checkin.avg_kcal_intake is not None else None,
        "weight_change_kg": float(checkin.weight_change_kg) if checkin.weight_change_kg is not None else None,
        "data_quality_result": checkin.data_quality_result,
        "adherence_result": checkin.adherence_result,
        "outcome_result": checkin.outcome_result,
        "safety_flags": checkin.safety_flags or [],
        "recommendation": checkin.recommendation,
        "recommendation_reason": checkin.recommendation_reason,
        "proposed_kcal_target": checkin.proposed_kcal_target,
        "ai_feedback": checkin.ai_feedback,
        "feedback_status": checkin.feedback_status,
        "decision": checkin.decision,
        "adjusted_plan_id": checkin.adjusted_plan_id,
    }


def _latest_weight(db: Session, user: User) -> float | None:
    row = latest_body_metric(db, user.id)
    if row and row.weight_kg is not None:
        return float(row.weight_kg)
    return None


def _new_period(
    series: PlanCheckinSeries,
    user: User,
    plan: NutritionPlan,
    period_number: int,
    start_date: date,
    baseline_weight: float,
    previous_checkin_id=None,
) -> PlanCheckin:
    expected_min, expected_max = expected_weight_range(baseline_weight, str(plan.goal))
    return PlanCheckin(
        series_id=series.id,
        user_id=user.id,
        plan_id=plan.id,
        previous_checkin_id=previous_checkin_id,
        period_number=period_number,
        start_date=start_date,
        period_end=start_date + timedelta(days=PERIOD_DAYS - 1),
        due_date=start_date + timedelta(days=PERIOD_DAYS),
        grace_until=start_date + timedelta(days=PERIOD_DAYS + GRACE_DAYS),
        baseline_weight_kg=baseline_weight,
        goal_snapshot=plan.goal,
        target_kcal_snapshot=plan.daily_kcal_target,
        activity_target_snapshot=user.profile.activity_level if user.profile else None,
        expected_weight_min_kg=expected_min,
        expected_weight_max_kg=expected_max,
        prediction_rule_version=PREDICTION_RULE_VERSION,
        status="OPEN",
    )


def start_new_series(db: Session, user: User, plan: NutritionPlan, today: date | None = None) -> PlanCheckin:
    """Đóng chuỗi/kỳ cũ và tạo kỳ đầu tiên cho plan vừa áp dụng."""
    today = today or date.today()
    baseline = _latest_weight(db, user)
    if baseline is None:
        raise ValueError("Cần cập nhật cân nặng trước khi tạo lộ trình")

    open_rows = db.query(PlanCheckin).filter(
        PlanCheckin.user_id == user.id, PlanCheckin.status == "OPEN"  # type: ignore
    ).all()
    for row in open_rows:
        row.status = "CANCELLED"  # type: ignore

    active_series = db.query(PlanCheckinSeries).filter(
        PlanCheckinSeries.user_id == user.id, PlanCheckinSeries.status == "ACTIVE"  # type: ignore
    ).all()
    for series in active_series:
        series.status = "CLOSED"  # type: ignore
        series.closed_at = today  # type: ignore
    db.flush()

    series = PlanCheckinSeries(user_id=user.id, goal=plan.goal, status="ACTIVE", started_at=today)
    db.add(series)
    db.flush()
    checkin = _new_period(series, user, plan, 1, today, baseline)
    db.add(checkin)
    if plan.end_date < checkin.period_end:
        plan.end_date = checkin.period_end  # type: ignore
    db.flush()
    return checkin


def create_next_period(
    db: Session,
    user: User,
    previous: PlanCheckin,
    plan: NutritionPlan,
    today: date | None = None,
) -> PlanCheckin:
    """Tạo đúng một kỳ kế tiếp, bắt đầu từ ngày ra quyết định."""
    existing = db.query(PlanCheckin).filter(
        PlanCheckin.user_id == user.id, PlanCheckin.status == "OPEN"  # type: ignore
    ).first()
    if existing:
        return existing
    baseline = (
        float(previous.actual_weight_kg)
        if previous.actual_weight_kg is not None
        else _latest_weight(db, user)
    )
    if baseline is None:
        raise ValueError("Cần cập nhật cân nặng trước khi bắt đầu kỳ tiếp theo")
    series = db.query(PlanCheckinSeries).filter(PlanCheckinSeries.id == previous.series_id).one()
    checkin = _new_period(
        series, user, plan, previous.period_number + 1, today or date.today(), baseline, previous.id
    )
    db.add(checkin)
    if plan.end_date < checkin.period_end:
        plan.end_date = checkin.period_end  # type: ignore
    db.flush()
    return checkin


def simulate_due_checkin(
    db: Session,
    user: User,
    today: date | None = None,
) -> PlanCheckin:
    """Đưa kỳ đang chờ về ngày đến hạn để kiểm thử, không thay đổi ngày hệ thống."""
    today = today or date.today()
    checkin = (
        db.query(PlanCheckin)
        .filter(PlanCheckin.user_id == user.id, PlanCheckin.status == "OPEN")  # type: ignore
        .with_for_update()
        .one_or_none()
    )
    if checkin is None:
        raise LookupError("Không có kỳ check-in đang mở")
    if display_status(checkin.status, checkin.due_date, checkin.grace_until, today) != "UPCOMING":
        raise RuntimeError("Kỳ check-in hiện tại đã đến hạn hoặc đã được xử lý")

    checkin.start_date = today - timedelta(days=PERIOD_DAYS)  # type: ignore
    checkin.period_end = today - timedelta(days=1)  # type: ignore
    checkin.due_date = today  # type: ignore
    checkin.grace_until = today + timedelta(days=GRACE_DAYS)  # type: ignore
    checkin.updated_at = datetime.now(timezone.utc)  # type: ignore
    db.flush()
    return checkin


def get_current_checkin(db: Session, user: User, today: date | None = None) -> PlanCheckin | None:
    """Lấy kỳ cần hiển thị: ưu tiên OPEN, nếu không có thì kỳ hoàn tất gần nhất."""
    reconcile_overdue_checkin(db, user, today)
    return (
        db.query(PlanCheckin)
        .filter(PlanCheckin.user_id == user.id)  # type: ignore
        .order_by(
            (PlanCheckin.status == "OPEN").desc(),
            PlanCheckin.period_number.desc(),  # type: ignore
            PlanCheckin.start_date.desc(),  # type: ignore
        )
        .first()
    )


def reconcile_overdue_checkin(db: Session, user: User, today: date | None = None) -> PlanCheckin | None:
    """Đóng kỳ hết gia hạn và tạo kỳ mới với cùng plan; gọi lặp vẫn an toàn."""
    today = today or date.today()
    current = (
        db.query(PlanCheckin)
        .filter(PlanCheckin.user_id == user.id, PlanCheckin.status == "OPEN")  # type: ignore
        .with_for_update()
        .first()
    )
    if not current or today <= current.grace_until:
        return current
    current.status = "MISSED"  # type: ignore
    current.completed_at = datetime.now(timezone.utc)  # type: ignore
    db.flush()
    plan = db.query(NutritionPlan).filter(NutritionPlan.id == current.plan_id).one()
    return create_next_period(db, user, current, plan, today)


def _tracking_metrics(db: Session, checkin: PlanCheckin) -> tuple[int, float | None]:
    row = db.execute(text("""
        SELECT COUNT(DISTINCT log_date) AS days, SUM(calories_kcal) AS total
        FROM meal_logs
        WHERE user_id = :uid AND log_date BETWEEN :start AND :end
    """), {
        "uid": str(checkin.user_id),
        "start": checkin.start_date,
        "end": checkin.period_end,
    }).mappings().first()
    days = int(row["days"] or 0) if row else 0
    avg = float(row["total"] or 0) / PERIOD_DAYS if days else None
    return days, round(avg, 2) if avg is not None else None


def _previous_was_off_track(db: Session, checkin: PlanCheckin) -> bool:
    previous = db.query(PlanCheckin).filter(
        PlanCheckin.series_id == checkin.series_id,
        PlanCheckin.period_number == checkin.period_number - 1,  # type: ignore
        PlanCheckin.status == "COMPLETED",  # type: ignore
    ).first()
    unfavorable = (
        (checkin.goal_snapshot == "LOSE_WEIGHT" and previous and previous.outcome_result == "ABOVE_EXPECTED_RANGE")
        or (checkin.goal_snapshot == "GAIN_MUSCLE" and previous and previous.outcome_result == "BELOW_EXPECTED_RANGE")
    )
    return bool(previous and previous.data_quality_result == "SUFFICIENT"
                and previous.adherence_result == "HIGH" and unfavorable)


def _upsert_weight(db: Session, user: User, weight_kg: float, recorded_at: date) -> None:
    upsert_body_metric(db, user.id, weight_kg=weight_kg, recorded_at=recorded_at)


def submit_checkin(db: Session, user: User, checkin_id, payload, today: date | None = None) -> PlanCheckin:
    """Ghi và đánh giá check-in trong transaction do router quản lý."""
    today = today or date.today()
    checkin = (
        db.query(PlanCheckin)
        .filter(PlanCheckin.id == checkin_id, PlanCheckin.user_id == user.id)  # type: ignore
        .with_for_update()
        .first()
    )
    if not checkin:
        raise LookupError("Không tìm thấy kỳ check-in")
    if checkin.status == "COMPLETED":
        return checkin
    if checkin.status != "OPEN":
        raise RuntimeError("Kỳ check-in không còn nhận dữ liệu")
    if today < checkin.due_date:
        raise RuntimeError("Chưa đến ngày check-in")
    if today > checkin.grace_until:
        raise RuntimeError("Kỳ check-in đã quá hạn")

    baseline_weight = float(checkin.baseline_weight_kg)
    if abs(payload.actual_weight_kg - baseline_weight) / baseline_weight > 0.20:
        raise ValueError(
            f"Cân nặng thay đổi quá 20% so với đầu kỳ ({baseline_weight:g} kg). "
            "Vui lòng kiểm tra và nhập lại số liệu."
        )

    meal_days, avg_kcal = _tracking_metrics(db, checkin)
    quality = derive_data_quality(True, meal_days)
    adherence = derive_adherence(payload.adherence_pct)
    outcome = derive_outcome(
        payload.actual_weight_kg,
        float(checkin.expected_weight_min_kg),
        float(checkin.expected_weight_max_kg),
        quality,
        adherence,
    )
    flags = derive_safety_flags(
        float(checkin.baseline_weight_kg),
        payload.actual_weight_kg,
        payload.energy_level,
        payload.hunger_level,
        payload.sleep_quality,
        str(checkin.goal_snapshot),
    )
    recommendation = derive_recommendation(
        quality, adherence, outcome, flags, _previous_was_off_track(db, checkin), str(checkin.goal_snapshot)
    )

    checkin.actual_weight_kg = payload.actual_weight_kg  # type: ignore
    checkin.actual_waist_cm = payload.actual_waist_cm  # type: ignore
    checkin.actual_activity_level = payload.actual_activity_level  # type: ignore
    checkin.adherence_pct = payload.adherence_pct  # type: ignore
    checkin.energy_level = payload.energy_level  # type: ignore
    checkin.hunger_level = payload.hunger_level  # type: ignore
    checkin.sleep_quality = payload.sleep_quality  # type: ignore
    checkin.notes = payload.notes.strip() if payload.notes else None  # type: ignore
    checkin.meal_log_days = meal_days  # type: ignore
    checkin.avg_kcal_intake = avg_kcal  # type: ignore
    checkin.weight_change_kg = round(payload.actual_weight_kg - float(checkin.baseline_weight_kg), 2)  # type: ignore
    checkin.data_quality_result = quality  # type: ignore
    checkin.adherence_result = adherence  # type: ignore
    checkin.outcome_result = outcome  # type: ignore
    checkin.safety_flags = flags  # type: ignore
    checkin.recommendation = recommendation  # type: ignore
    checkin.recommendation_reason = RECOMMENDATION_REASONS[recommendation]  # type: ignore
    checkin.proposed_kcal_target = propose_kcal_target(  # type: ignore
        checkin.target_kcal_snapshot, str(checkin.goal_snapshot), recommendation
    )
    checkin.feedback_status = "PENDING"  # type: ignore
    checkin.status = "COMPLETED"  # type: ignore
    checkin.submitted_at = datetime.now(timezone.utc)  # type: ignore
    checkin.completed_at = datetime.now(timezone.utc)  # type: ignore
    _upsert_weight(db, user, payload.actual_weight_kg, today)
    db.flush()
    return checkin


def reopen_checkin(db: Session, user: User, checkin_id) -> PlanCheckin:
    """Mở lại báo cáo chưa có quyết định để người dùng sửa số liệu nhập nhầm."""
    checkin = (
        db.query(PlanCheckin)
        .filter(PlanCheckin.id == checkin_id, PlanCheckin.user_id == user.id)  # type: ignore
        .with_for_update()
        .first()
    )
    if not checkin:
        raise LookupError("Không tìm thấy kỳ check-in")
    if checkin.status != "COMPLETED" or checkin.decision:
        raise RuntimeError("Chỉ có thể sửa báo cáo đã gửi nhưng chưa chọn quyết định")

    checkin.status = "OPEN"  # type: ignore
    checkin.feedback_status = "NOT_REQUESTED"  # type: ignore
    checkin.ai_feedback = None  # type: ignore
    checkin.submitted_at = None  # type: ignore
    checkin.completed_at = None  # type: ignore
    checkin.updated_at = datetime.now(timezone.utc)  # type: ignore
    db.flush()
    return checkin


def decide_checkin(db: Session, user: User, checkin_id, action: str) -> tuple[PlanCheckin, PlanCheckin]:
    """Ghi quyết định một lần và tạo kỳ tiếp theo; adjustment tạo plan version mới."""
    checkin = (
        db.query(PlanCheckin)
        .filter(PlanCheckin.id == checkin_id, PlanCheckin.user_id == user.id)  # type: ignore
        .with_for_update()
        .first()
    )
    if not checkin:
        raise LookupError("Không tìm thấy kỳ check-in")
    if checkin.status != "COMPLETED":
        raise RuntimeError("Kỳ check-in chưa hoàn tất")
    if checkin.decision:
        next_period = db.query(PlanCheckin).filter(
            PlanCheckin.previous_checkin_id == checkin.id  # type: ignore
        ).first()
        if not next_period:
            raise RuntimeError("Quyết định cũ chưa tạo được kỳ tiếp theo")
        return checkin, next_period

    plan = db.query(NutritionPlan).filter(NutritionPlan.id == checkin.plan_id).one()
    next_plan = plan
    if action == "APPLY_ADJUSTMENT":
        if checkin.recommendation != "ADJUST_PLAN" or checkin.proposed_kcal_target is None:
            raise RuntimeError("Kết quả hiện tại không cho phép điều chỉnh tự động")
        from app.services import plan_generator

        note = (
            f"Check-in kỳ {checkin.period_number}: {checkin.recommendation_reason} "
            f"Cân nặng thay đổi {float(checkin.weight_change_kg or 0):+.1f} kg."
        )
        next_plan = plan_generator.create_plan(
            db, user, target=checkin.proposed_kcal_target, note=note
        )
        next_plan.parent_plan_id = plan.id  # type: ignore
        db.flush()
        checkin.adjusted_plan_id = next_plan.id  # type: ignore
        checkin.adjustment_applied_at = datetime.now(timezone.utc)  # type: ignore
    elif action != "CONTINUE":
        raise ValueError("Quyết định không hợp lệ")

    checkin.decision = action  # type: ignore
    checkin.decision_at = datetime.now(timezone.utc)  # type: ignore
    next_period = create_next_period(db, user, checkin, next_plan)
    db.flush()
    return checkin, next_period


# ---------- Phản hồi AI nền ----------

def _fallback_feedback(checkin: PlanCheckin) -> str:
    return (
        f"Kết quả kỳ {checkin.period_number}: {checkin.recommendation_reason} "
        "Hãy tiếp tục ghi nhật ký đều đặn và theo dõi cảm nhận cơ thể."
    )


def generate_feedback(checkin: PlanCheckin) -> tuple[str, str]:
    prompt = f"""Bạn là chuyên gia dinh dưỡng. Viết tối đa 3 câu tiếng Việt, không markdown.
Chỉ diễn giải kết quả đã được hệ thống quyết định, không thay đổi recommendation và không chẩn đoán bệnh.
Mục tiêu: {checkin.goal_snapshot}; kcal: {checkin.target_kcal_snapshot};
thay đổi cân nặng: {checkin.weight_change_kg} kg; tuân thủ: {checkin.adherence_pct}%;
năng lượng/đói/ngủ: {checkin.energy_level}/{checkin.hunger_level}/{checkin.sleep_quality};
recommendation: {checkin.recommendation}; lý do: {checkin.recommendation_reason}."""
    try:
        feedback = ollama_client.chat(
            [{"role": "user", "content": prompt}], timeout=60.0, options={"num_predict": 180}
        )
        return feedback, "COMPLETED"
    except Exception as exc:
        logger.warning("Không sinh được feedback check-in %s: %s", checkin.id, exc)
        return _fallback_feedback(checkin), "FAILED"


def process_pending_feedback(db: Session, limit: int = 10) -> int:
    rows = (
        db.query(PlanCheckin)
        .filter(PlanCheckin.feedback_status == "PENDING")  # type: ignore
        .order_by(PlanCheckin.submitted_at)
        .limit(limit)
        .all()
    )
    for row in rows:
        feedback, feedback_status = generate_feedback(row)
        db.refresh(row)
        # Người dùng có thể mở lại báo cáo trong lúc Ollama đang chạy.
        if row.status != "COMPLETED" or row.feedback_status != "PENDING":
            continue
        row.ai_feedback = feedback  # type: ignore
        row.feedback_status = feedback_status  # type: ignore
        db.commit()
    return len(rows)


def create_due_notifications(db: Session, today: date | None = None) -> int:
    """Tạo nhắc hạn theo dedupe key để job chạy lặp không gửi trùng."""
    today = today or date.today()
    rows = db.query(PlanCheckin).filter(PlanCheckin.status == "OPEN").all()  # type: ignore
    created = 0
    for row in rows:
        kind = None
        title = None
        body = None
        if today == row.due_date - timedelta(days=2):
            kind = "CHECKIN_UPCOMING"
            title = "Sắp đến ngày báo cáo tiến độ"
            body = "Còn 2 ngày nữa đến kỳ check-in. Hãy tiếp tục ghi nhật ký đầy đủ."
        elif today == row.due_date:
            kind = "CHECKIN_DUE"
            title = "Đã đến ngày check-in 14 ngày"
            body = "Hãy cập nhật cân nặng và cảm nhận để hệ thống đánh giá tiến độ."
        elif row.due_date < today <= row.grace_until:
            kind = "CHECKIN_LATE"
            title = "Bạn chưa hoàn tất check-in"
            body = f"Bạn vẫn có thể gửi báo cáo đến hết ngày {row.grace_until}."
        if not kind:
            continue
        key = f"checkin:{row.id}:{kind}"
        exists = db.query(Notification).filter(Notification.dedupe_key == key).first()  # type: ignore
        if exists:
            continue
        db.add(Notification(
            user_id=row.user_id, type=kind, title=title, body=body, dedupe_key=key
        ))
        created += 1
    return created


async def scheduler_loop() -> None:
    """Job bền vững theo DB: reconcile kỳ quá hạn và xử lý feedback đang chờ."""
    from app.database import SessionLocal

    await asyncio.sleep(settings.PLAN_CHECKIN_DELAY_SECONDS)
    while True:
        db = SessionLocal()
        try:
            users = db.query(User).all()
            for user in users:
                reconcile_overdue_checkin(db, user)
            create_due_notifications(db)
            db.commit()
            process_pending_feedback(db)
        except Exception:
            db.rollback()
            logger.exception("Job check-in 14 ngày gặp lỗi")
        finally:
            db.close()
        await asyncio.sleep(settings.PLAN_CHECKIN_INTERVAL_MINUTES * 60)

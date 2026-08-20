"""Lưu tiến độ ngày và đồng bộ nhật ký từ lộ trình theo cách idempotent."""

from datetime import date, datetime, time, timedelta, timezone
import re

from sqlalchemy.orm import Session

from app.models import (
    ActivityLog,
    MealLog,
    NutritionPlan,
    PlanCheckin,
    PlanCheckinSeries,
    PlanDailyProgress,
    User,
)


ITEM_KEYS = ("meal:0", "meal:1", "meal:2", "exercise")
MEAL_TYPES = {
    "sáng": "BREAKFAST",
    "trưa": "LUNCH",
    "tối": "DINNER",
    "phụ": "SNACK",
}
LOCAL_TIMEZONE = timezone(timedelta(hours=7))
LEGACY_DURATION_PATTERN = re.compile(
    r"(?P<value>\d+(?:[.,]\d+)?)\s*(?:phút|phut|minutes?|mins?)",
    re.IGNORECASE,
)
LEGACY_CALORIES_PATTERN = re.compile(
    r"(?P<value>\d+(?:[.,]\d+)?)\s*kcal",
    re.IGNORECASE,
)


def _ordered_items(values: list[str]) -> list[str]:
    selected = set(values)
    unknown = selected.difference(ITEM_KEYS)
    if unknown:
        raise ValueError("Mục tiến độ không hợp lệ")
    return [key for key in ITEM_KEYS if key in selected]


def _meal_type(value: str) -> str:
    normalized = value.strip().casefold()
    for label, result in MEAL_TYPES.items():
        if label in normalized:
            return result
    return "LUNCH"


def _exercise_data(day: dict) -> tuple[str, int, float]:
    exercise = day.get("exercise")
    if isinstance(exercise, dict):
        return (
            str(exercise.get("name") or "Vận động theo lộ trình"),
            int(exercise.get("duration_min") or 0),
            float(exercise.get("calories_kcal") or 0),
        )
    if not exercise:
        return "Vận động theo lộ trình", 0, 0.0

    text = str(exercise).strip()
    duration_match = LEGACY_DURATION_PATTERN.search(text)
    calories_match = LEGACY_CALORIES_PATTERN.search(text)
    duration = int(float(duration_match.group("value").replace(",", "."))) if duration_match else 0
    calories = float(calories_match.group("value").replace(",", ".")) if calories_match else 0.0
    metric_starts = [
        match.start() for match in (duration_match, calories_match) if match is not None
    ]
    name = text[:min(metric_starts)].rstrip(" -–—·,:") if metric_starts else text
    return name or "Vận động theo lộ trình", duration, calories


def _context(
    db: Session,
    user: User,
    plan_id,
    progress_date: date,
    today: date,
) -> tuple[NutritionPlan, PlanCheckin, PlanCheckinSeries, dict, int]:
    if progress_date > today:
        raise ValueError("Không thể cập nhật tiến độ ngày tương lai")

    plan = db.query(NutritionPlan).filter(
        NutritionPlan.id == plan_id,  # type: ignore
        NutritionPlan.user_id == user.id,  # type: ignore
    ).first()
    if plan is None:
        raise LookupError("Không tìm thấy lộ trình")

    checkin = db.query(PlanCheckin).filter(
        PlanCheckin.user_id == user.id,
        PlanCheckin.plan_id == plan.id,
        PlanCheckin.start_date <= progress_date,  # type: ignore
        PlanCheckin.period_end >= progress_date,  # type: ignore
    ).order_by(PlanCheckin.period_number.desc()).first()  # type: ignore
    if checkin is None:
        raise ValueError("Ngày này không thuộc Đợt hiện tại của lộ trình")
    if checkin.status != "OPEN":
        raise RuntimeError("Đợt này đã khóa và không còn nhận thay đổi")

    series = db.query(PlanCheckinSeries).filter(PlanCheckinSeries.id == checkin.series_id).one()  # type: ignore
    if series.status != "ACTIVE":
        raise RuntimeError("Chương trình không còn hoạt động")

    days = (plan.content or {}).get("days") or []
    if len(days) != 7:
        raise ValueError("Lộ trình không có đủ mẫu thực đơn 7 ngày")
    template_index = (progress_date - series.started_at).days % 7
    return plan, checkin, series, days[template_index], template_index


def _source_logs(db: Session, progress_id) -> tuple[list[MealLog], list[ActivityLog]]:
    meals = db.query(MealLog).filter(
        MealLog.source_type == "PLAN",  # type: ignore
        MealLog.source_progress_id == progress_id,
    ).all()
    activities = db.query(ActivityLog).filter(
        ActivityLog.source_type == "PLAN",  # type: ignore
        ActivityLog.source_progress_id == progress_id,
    ).all()
    return meals, activities


def _to_dict(
    progress: PlanDailyProgress,
    *,
    kcal_intake_delta: float = 0,
    kcal_burned_delta: float = 0,
) -> dict:
    return {
        "id": progress.id,
        "plan_id": progress.plan_id,
        "checkin_id": progress.checkin_id,
        "progress_date": progress.progress_date,
        "template_day_index": progress.template_day_index,
        "checked_items": progress.checked_items or [],
        "status": progress.status,
        "kcal_intake_delta": round(kcal_intake_delta, 2),
        "kcal_burned_delta": round(kcal_burned_delta, 2),
    }


def save_progress(
    db: Session,
    user: User,
    plan_id,
    progress_date: date,
    checked_items: list[str],
    *,
    today: date | None = None,
) -> dict:
    """Upsert tiến độ và biến đổi log tương ứng trong transaction của caller."""
    today = today or date.today()
    plan, checkin, series, day, template_index = _context(
        db, user, plan_id, progress_date, today
    )
    desired = _ordered_items(checked_items)

    progress = db.query(PlanDailyProgress).filter(
        PlanDailyProgress.checkin_id == checkin.id,
        PlanDailyProgress.progress_date == progress_date,  # type: ignore
    ).with_for_update().first()
    if progress is None:
        progress = PlanDailyProgress(
            user_id=user.id,
            series_id=series.id,
            checkin_id=checkin.id,
            plan_id=plan.id,
            progress_date=progress_date,
            template_day_index=template_index,
            checked_items=[],
            status="IN_PROGRESS",
        )
        db.add(progress)
        db.flush()
    old_meals, old_activities = _source_logs(db, progress.id)
    old_intake = sum(float(row.calories_kcal or 0) for row in old_meals)
    old_burned = sum(float(row.calories_burned or 0) for row in old_activities)
    meal_by_key = {str(row.source_item_key): row for row in old_meals}
    activity_by_key = {str(row.source_item_key): row for row in old_activities}

    desired_set = set(desired)
    for row in old_meals:
        if row.source_item_key not in desired_set:
            db.delete(row)
    for row in old_activities:
        if row.source_item_key not in desired_set:
            db.delete(row)

    meals = day.get("meals") or []
    for index, meal in enumerate(meals[:3]):
        key = f"meal:{index}"
        if key not in desired_set or key in meal_by_key:
            continue
        db.add(MealLog(
            user_id=user.id,
            meal_type=_meal_type(str(meal.get("type") or "")),
            quantity=1,
            calories_kcal=float(meal.get("kcal") or 0),
            log_date=progress_date,
            source_type="PLAN",
            source_progress_id=progress.id,
            source_item_key=key,
            item_name_snapshot=str(meal.get("name") or "Bữa ăn theo lộ trình"),
        ))

    if "exercise" in desired_set:
        name, duration, calories = _exercise_data(day)
        started_at = datetime.combine(progress_date, time(hour=12), tzinfo=LOCAL_TIMEZONE)
        existing_activity = activity_by_key.get("exercise")
        if existing_activity is not None:
            existing_activity.duration_min = duration
            existing_activity.calories_burned = calories
            existing_activity.item_name_snapshot = name
            setattr(
                existing_activity,
                "ended_at",
                started_at + timedelta(minutes=duration) if duration else None,
            )
        else:
            db.add(ActivityLog(
                user_id=user.id,
                duration_min=duration,
                calories_burned=calories,
                started_at=started_at,
                ended_at=started_at + timedelta(minutes=duration) if duration else None,
                source_type="PLAN",
                source_progress_id=progress.id,
                source_item_key="exercise",
                item_name_snapshot=name,
            ))

    progress.checked_items = desired  # type: ignore
    progress.updated_at = datetime.now(timezone.utc)  # type: ignore
    db.flush()
    new_meals, new_activities = _source_logs(db, progress.id)
    new_intake = sum(float(row.calories_kcal or 0) for row in new_meals)
    new_burned = sum(float(row.calories_burned or 0) for row in new_activities)
    return _to_dict(
        progress,
        kcal_intake_delta=new_intake - old_intake,
        kcal_burned_delta=new_burned - old_burned,
    )


def complete_progress(
    db: Session,
    user: User,
    plan_id,
    progress_date: date,
    checked_items: list[str],
    *,
    today: date | None = None,
) -> dict:
    result = save_progress(
        db, user, plan_id, progress_date, checked_items, today=today
    )
    progress = db.query(PlanDailyProgress).filter(PlanDailyProgress.id == result["id"]).one()  # type: ignore
    progress.status = "COMPLETED"  # type: ignore
    progress.completed_at = datetime.now(timezone.utc)  # type: ignore
    progress.updated_at = datetime.now(timezone.utc)  # type: ignore
    db.flush()
    return {
        **result,
        "status": "COMPLETED",
    }


def reset_progress(
    db: Session,
    user: User,
    plan_id,
    progress_date: date,
    *,
    today: date | None = None,
) -> dict:
    today = today or date.today()
    plan, checkin, series, _, template_index = _context(db, user, plan_id, progress_date, today)
    progress = db.query(PlanDailyProgress).filter(
        PlanDailyProgress.checkin_id == checkin.id,
        PlanDailyProgress.progress_date == progress_date,  # type: ignore
    ).with_for_update().first()
    if progress is None:
        progress = PlanDailyProgress(
            user_id=user.id,
            series_id=series.id,
            checkin_id=checkin.id,
            plan_id=plan.id,
            progress_date=progress_date,
            template_day_index=template_index,
            checked_items=[],
            status="IN_PROGRESS",
        )
        db.add(progress)
        db.flush()
        return _to_dict(progress)
    meals, activities = _source_logs(db, progress.id)
    intake = sum(float(row.calories_kcal or 0) for row in meals)
    burned = sum(float(row.calories_burned or 0) for row in activities)
    for row in [*meals, *activities]:
        db.delete(row)
    progress.checked_items = []  # type: ignore
    progress.status = "IN_PROGRESS"  # type: ignore
    progress.completed_at = None  # type: ignore
    progress.updated_at = datetime.now(timezone.utc)  # type: ignore
    db.flush()
    return _to_dict(
        progress,
        kcal_intake_delta=-intake,
        kcal_burned_delta=-burned,
    )


def list_progress(db: Session, user: User, checkin: PlanCheckin) -> list[dict]:
    rows = db.query(PlanDailyProgress).filter(
        PlanDailyProgress.user_id == user.id,
        PlanDailyProgress.checkin_id == checkin.id,
    ).order_by(PlanDailyProgress.progress_date).all()  # type: ignore
    return [_to_dict(row) for row in rows]


def get_progress(
    db: Session,
    user: User,
    plan_id,
    progress_date: date,
    *,
    today: date | None = None,
) -> dict:
    today = today or date.today()
    plan, checkin, _, _, template_index = _context(db, user, plan_id, progress_date, today)
    row = db.query(PlanDailyProgress).filter(
        PlanDailyProgress.user_id == user.id,
        PlanDailyProgress.plan_id == plan.id,
        PlanDailyProgress.checkin_id == checkin.id,
        PlanDailyProgress.progress_date == progress_date,  # type: ignore
    ).first()
    if row is not None:
        return _to_dict(row)
    return {
        "id": None,
        "plan_id": plan.id,
        "checkin_id": checkin.id,
        "progress_date": progress_date,
        "template_day_index": template_index,
        "checked_items": [],
        "status": "IN_PROGRESS",
        "kcal_intake_delta": 0,
        "kcal_burned_delta": 0,
    }

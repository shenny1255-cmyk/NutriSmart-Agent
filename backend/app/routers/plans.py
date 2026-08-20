from datetime import date
from typing import cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.deps import get_db, get_current_user, require_role
from app.config import settings
from app.models import User, NutritionPlan, PlanCheckin, PlanCheckinSeries, PlanEvaluation
from app.schemas import (
    CheckinDecisionIn,
    CheckinSubmitIn,
    PlanCheckinOut,
    PlanExtendIn,
    PlanGenerateIn,
    PlanProgressIn,
)
from app.services import (
    body_metrics,
    plan_checkin,
    plan_evaluator,
    plan_generator,
    plan_jobs,
    plan_progress,
)
from app.services.activity_levels import get_activity_level
from app.services.calorie import daily_calorie_target
from app.services.nutrition_context import gather_context
from app.schemas import validate_body_metrics

router = APIRouter(prefix="/plans", tags=["plans"])

PLAN_PROFILE_FIELDS = (
    ("profile", "gender", "giới tính"),
    ("profile", "birth_date", "ngày sinh"),
    ("metric", "height_cm", "chiều cao"),
    ("metric", "weight_kg", "cân nặng"),
    ("profile", "activity_level", "mức vận động"),
    ("profile", "goal", "mục tiêu"),
)


def _join_vietnamese(items: list[str]) -> str:
    if len(items) <= 1:
        return "".join(items)
    return f"{', '.join(items[:-1])} và {items[-1]}"


def _require_complete_profile_for_plan(db: Session, user: User) -> None:
    profile = user.profile
    metric = body_metrics.latest_body_metric(db, user.id)
    sources = {"profile": profile, "metric": metric}
    missing = [
        label for source, field, label in PLAN_PROFILE_FIELDS
        if sources[source] is None or getattr(sources[source], field, None) in (None, "")
    ]
    if missing:
        raise HTTPException(
            422,
            f"Bạn chưa cập nhật {_join_vietnamese(missing)}. "
            "Vui lòng hoàn thiện hồ sơ trước khi tạo lộ trình.",
        )


def _active_plan_or_404(db: Session, user: User) -> NutritionPlan:
    plan = plan_evaluator.active_plan(db, user)
    if not plan:
        raise HTTPException(404, "Chưa có lộ trình nào")
    return plan


def _visible_plan_or_404(db: Session, user: User) -> NutritionPlan:
    plan = plan_evaluator.active_plan(db, user)
    if plan is None:
        plan = (
            db.query(NutritionPlan)
            .filter(
                NutritionPlan.user_id == user.id,
                NutritionPlan.status == "COMPLETED",  # type: ignore
            )
            .order_by(NutritionPlan.version.desc())  # type: ignore
            .first()
        )
    if plan is None:
        raise HTTPException(404, "Chưa có lộ trình nào")
    return plan


def _program_to_dict(db: Session, series, current: PlanCheckin) -> dict:
    completed_periods = db.query(PlanCheckin).filter(
        PlanCheckin.series_id == series.id,
        PlanCheckin.decision.isnot(None),  # type: ignore
    ).count()
    return {
        "id": series.id,
        "status": series.status,
        "duration_months": series.duration_months,
        "started_at": series.started_at,
        "planned_end_date": series.planned_end_date,
        "total_periods": plan_checkin.total_program_periods(int(series.duration_months)),
        "completed_periods": completed_periods,
        "is_final_period": current.period_number >= plan_checkin.total_program_periods(
            int(series.duration_months)
        ),
    }


@router.get("/active")
def active_plan(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    plan = _visible_plan_or_404(db, user)

    res = plan_generator.plan_to_dict(db, plan, user)
    res["days_elapsed"] = (date.today() - plan.start_date).days  # type: ignore
    try:
        current = (
            plan_checkin.get_current_checkin(db, user)
            if plan.status == "ACTIVE"
            else db.query(PlanCheckin).filter(
                PlanCheckin.user_id == user.id,
                PlanCheckin.plan_id == plan.id,
            ).order_by(PlanCheckin.period_number.desc()).first()  # type: ignore
        )
        if current is None and plan.status == "ACTIVE":
            current = plan_checkin.start_new_series(db, user, plan)
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(400, str(exc)) from exc
    if current is None:
        res["current_checkin"] = None
        res["program"] = None
        res["daily_progress"] = []
        return res
    series = db.query(PlanCheckinSeries).filter(
        PlanCheckinSeries.id == current.series_id  # type: ignore
    ).one()
    current_data = plan_checkin.checkin_to_dict(current)
    program_data = _program_to_dict(db, series, current)
    current_data["total_periods"] = program_data["total_periods"]
    current_data["is_final_period"] = program_data["is_final_period"]
    res["current_checkin"] = current_data
    res["program"] = program_data
    res["daily_progress"] = plan_progress.list_progress(db, user, current)
    res["program_summary"] = (
        plan_checkin.program_summary(db, user, series)
        if series.status == "COMPLETED" else None
    )
    return res


def _latest_series_or_404(db: Session, user: User) -> PlanCheckinSeries:
    series = (
        db.query(PlanCheckinSeries)
        .filter(PlanCheckinSeries.user_id == user.id)
        .order_by(
            PlanCheckinSeries.started_at.desc(),  # type: ignore
            PlanCheckinSeries.created_at.desc(),  # type: ignore
        )
        .first()
    )
    if series is None:
        raise HTTPException(404, "Không tìm thấy chương trình")
    return series


@router.get("/programs/current/summary")
def current_program_summary(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return plan_checkin.program_summary(db, user, _latest_series_or_404(db, user))


@router.post("/programs/current/extend")
def extend_current_program(
    payload: PlanExtendIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        series, next_period = plan_checkin.extend_program(
            db, user, payload.additional_months
        )
        db.commit()
        return {
            "program": _program_to_dict(db, series, next_period),
            "next_checkin": plan_checkin.checkin_to_dict(next_period),
        }
    except LookupError as exc:
        db.rollback()
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(422, str(exc)) from exc
    except RuntimeError as exc:
        db.rollback()
        raise HTTPException(409, str(exc)) from exc
    except Exception:
        db.rollback()
        raise


def _progress_call(db: Session, action):
    try:
        return action()
    except LookupError as exc:
        db.rollback()
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(422, str(exc)) from exc
    except RuntimeError as exc:
        db.rollback()
        raise HTTPException(409, str(exc)) from exc
    except Exception:
        db.rollback()
        raise


@router.get("/{plan_id}/days/{progress_date}/progress")
def day_progress(
    plan_id: UUID,
    progress_date: date,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return _progress_call(db,
        lambda: plan_progress.get_progress(db, user, plan_id, progress_date)
    )


@router.put("/{plan_id}/days/{progress_date}/progress")
def save_day_progress(
    plan_id: UUID,
    progress_date: date,
    payload: PlanProgressIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    def action():
        result = plan_progress.save_progress(
            db, user, plan_id, progress_date, cast(list[str], payload.checked_items)
        )
        db.commit()
        return result
    return _progress_call(db, action)


@router.post("/{plan_id}/days/{progress_date}/complete")
def complete_day_progress(
    plan_id: UUID,
    progress_date: date,
    payload: PlanProgressIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    def action():
        result = plan_progress.complete_progress(
            db, user, plan_id, progress_date, cast(list[str], payload.checked_items)
        )
        db.commit()
        return result
    return _progress_call(db, action)


@router.delete("/{plan_id}/days/{progress_date}/progress")
def reset_day_progress(
    plan_id: UUID,
    progress_date: date,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    def action():
        result = plan_progress.reset_progress(db, user, plan_id, progress_date)
        db.commit()
        return result
    return _progress_call(db, action)


@router.post("/generate", status_code=202)
def generate_plan(
    payload: PlanGenerateIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Sinh thực đơn bằng LLM dựa trên profile + bệnh nền + dị ứng + calo mục tiêu."""
    _require_complete_profile_for_plan(db, user)
    baseline = body_metrics.latest_body_metric(db, user.id)
    active = plan_evaluator.active_plan(db, user)

    if active is not None:
        if not payload.confirm_recreate:
            raise HTTPException(409, "Bạn cần xác nhận trước khi kết thúc chương trình hiện tại")
        if payload.expected_active_plan_id != active.id:
            raise HTTPException(409, "Lộ trình hiện tại đã thay đổi; vui lòng tải lại trang")

        current = plan_checkin.get_current_checkin(db, user)
        if current and current.status == "COMPLETED" and not current.decision:
            raise HTTPException(409, "Vui lòng chốt quyết định check-in trước khi tạo chương trình mới")

    if baseline and baseline.weight_kg is not None:
        previous_weight = float(baseline.weight_kg)
        if abs(payload.weight_kg - previous_weight) / previous_weight > 0.10:
            raise HTTPException(
                422,
                f"Cân nặng thay đổi quá 10% so với lần gần nhất ({previous_weight:g} kg). "
                "Vui lòng kiểm tra hoặc cập nhật số đo tại Hồ sơ.",
            )

    target, profile_snapshot = _save_generation_metrics(db, user, payload)
    job = plan_jobs.enqueue(
        user.id,
        target_kcal=target,
        duration_months=payload.duration_months,
        expected_active_plan_id=active.id if active else None,
        profile_data=profile_snapshot,
        baseline_weight_kg=payload.weight_kg,
    )
    return {"job_id": job.id, "status": job.status}


def _save_generation_metrics(
    db: Session,
    user: User,
    payload: PlanGenerateIn,
) -> tuple[int, dict]:
    """Lưu số đo đã xác nhận và trả calorie target làm snapshot cho job."""
    info = user.profile
    if info is None or info.gender is None or info.birth_date is None or info.activity_level is None:
        raise HTTPException(422, "Vui lòng hoàn thiện hồ sơ trước khi tạo lộ trình")

    validate_body_metrics(payload.height_cm, payload.weight_kg)
    activity = get_activity_level(db, int(info.activity_level))
    target = daily_calorie_target(
        gender=str(info.gender),
        birth_date=info.birth_date,
        height_cm=payload.height_cm,
        weight_kg=payload.weight_kg,
        activity_multiplier=float(activity.calorie_multiplier),
        goal=str(info.goal),
    )
    body_metrics.upsert_body_metric(
        db,
        user.id,
        height_cm=payload.height_cm,
        weight_kg=payload.weight_kg,
    )
    info.daily_calorie_target = target  # type: ignore
    db.commit()
    profile_snapshot = dict(gather_context(db, user).get("profile") or {})
    profile_snapshot.update({
        "height_cm": payload.height_cm,
        "weight_kg": payload.weight_kg,
        "bmi": round(payload.weight_kg / ((payload.height_cm / 100) ** 2), 2),
        "goal": str(info.goal),
    })
    return target, profile_snapshot


@router.get("/generate/{job_id}")
def generate_plan_status(
    job_id: str,
    user: User = Depends(get_current_user),
):
    job = plan_jobs.get(job_id, user.id)
    if not job:
        raise HTTPException(404, "Không tìm thấy tác vụ sinh lộ trình")
    if job.status == "DONE":
        return {"job_id": job.id, "status": job.status, "plan_id": job.plan_id}
    if job.status == "FAILED":
        return {"job_id": job.id, "status": job.status,
                "error": job.error or "Không thể tạo lộ trình"}
    return {"job_id": job.id, "status": job.status}


@router.post("/evaluate", include_in_schema=False)
def evaluate_plan(
    force: bool = Query(False, description="Chấm ngay dù chưa đủ 7 ngày (dùng để demo)"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Endpoint cũ đã được thay bằng check-in 14 ngày."""
    raise HTTPException(410, "Đánh giá 7 ngày đã được thay bằng check-in tiến độ 14 ngày")


def _current_checkin_or_create(db: Session, user: User) -> PlanCheckin:
    current = plan_checkin.get_current_checkin(db, user)
    if current and current.status == "OPEN":
        return current
    plan = _active_plan_or_404(db, user)
    if current is None:
        return plan_checkin.start_new_series(db, user, plan)
    return current


@router.get("/active/checkin", response_model=PlanCheckinOut)
def active_checkin(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        current = _current_checkin_or_create(db, user)
        db.commit()
        return plan_checkin.checkin_to_dict(current)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(400, str(exc)) from exc


@router.get("/checkins/history", response_model=list[PlanCheckinOut])
def checkin_history(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rows = (
        db.query(PlanCheckin)
        .filter(PlanCheckin.user_id == user.id, PlanCheckin.status != "OPEN")  # type: ignore
        .order_by(PlanCheckin.start_date.desc())  # type: ignore
        .limit(limit)
        .all()
    )
    return [plan_checkin.checkin_to_dict(row) for row in rows]


@router.post("/checkins/current/simulate-due", response_model=PlanCheckinOut)
def simulate_current_checkin_due(
    db: Session = Depends(get_db),
    user: User = Depends(require_role("ADMIN")),
):
    """Công cụ thử nghiệm: đưa kỳ hiện tại đến hạn mà không đổi ngày máy."""
    if settings.APP_ENV.lower() == "production":
        raise HTTPException(404, "Không tìm thấy chức năng này")
    try:
        checkin = plan_checkin.simulate_due_checkin(db, user)
        db.commit()
        db.refresh(checkin)
        return plan_checkin.checkin_to_dict(checkin)
    except LookupError as exc:
        db.rollback()
        raise HTTPException(404, str(exc)) from exc
    except RuntimeError as exc:
        db.rollback()
        raise HTTPException(409, str(exc)) from exc


@router.post("/checkins/{checkin_id}/submit", response_model=PlanCheckinOut)
def submit_checkin(
    checkin_id: UUID,
    payload: CheckinSubmitIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        checkin = plan_checkin.submit_checkin(db, user, checkin_id, payload)
        db.commit()
        db.refresh(checkin)
        return plan_checkin.checkin_to_dict(checkin)
    except LookupError as exc:
        db.rollback()
        raise HTTPException(404, str(exc)) from exc
    except RuntimeError as exc:
        db.rollback()
        raise HTTPException(409, str(exc)) from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(422, str(exc)) from exc
    except Exception:
        db.rollback()
        raise


@router.post("/checkins/{checkin_id}/reopen", response_model=PlanCheckinOut)
def reopen_submitted_checkin(
    checkin_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        checkin = plan_checkin.reopen_checkin(db, user, checkin_id)
        db.commit()
        db.refresh(checkin)
        return plan_checkin.checkin_to_dict(checkin)
    except LookupError as exc:
        db.rollback()
        raise HTTPException(404, str(exc)) from exc
    except RuntimeError as exc:
        db.rollback()
        raise HTTPException(409, str(exc)) from exc


@router.post("/checkins/{checkin_id}/decision")
def decide_checkin(
    checkin_id: UUID,
    payload: CheckinDecisionIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        checkin, next_period = plan_checkin.decide_checkin(db, user, checkin_id, payload.action)
        db.commit()
        return {
            "checkin": plan_checkin.checkin_to_dict(checkin),
            "next_checkin": (
                plan_checkin.checkin_to_dict(next_period) if next_period is not None else None
            ),
        }
    except LookupError as exc:
        db.rollback()
        raise HTTPException(404, str(exc)) from exc
    except (RuntimeError, ValueError) as exc:
        db.rollback()
        raise HTTPException(409, str(exc)) from exc
    except Exception:
        db.rollback()
        raise


@router.get("/evaluations")
def list_evaluations(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Lịch sử chấm điểm các chu kỳ đã qua của người dùng."""
    rows = (
        db.query(PlanEvaluation, NutritionPlan.version)
        .join(NutritionPlan, NutritionPlan.id == PlanEvaluation.plan_id)  # type: ignore
        .filter(NutritionPlan.user_id == user.id)  # type: ignore
        .order_by(PlanEvaluation.period_start.desc())  # type: ignore
        .limit(limit)
        .all()
    )
    return [{**plan_evaluator.evaluation_to_dict(e), "plan_version": v} for e, v in rows]



@router.post("/jobs/evaluate-all", include_in_schema=False)
def evaluate_all(
    db: Session = Depends(get_db),
    _: User = Depends(require_role("ADMIN")),
):
    """Endpoint job cũ đã bị vô hiệu hóa để không sinh plan song song."""
    raise HTTPException(410, "Job đánh giá 7 ngày đã được thay bằng check-in 14 ngày")

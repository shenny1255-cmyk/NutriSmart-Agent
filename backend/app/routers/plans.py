from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.deps import get_db, get_current_user, require_role
from app.config import settings
from app.models import User, NutritionPlan, PlanCheckin, PlanEvaluation
from app.schemas import CheckinDecisionIn, CheckinSubmitIn, PlanCheckinOut
from app.services import body_metrics, plan_checkin, plan_evaluator, plan_generator, plan_jobs

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


@router.get("/active")
def active_plan(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    plan = _active_plan_or_404(db, user)

    res = plan_generator.plan_to_dict(db, plan, user)
    res["days_elapsed"] = (date.today() - plan.start_date).days  # type: ignore
    try:
        current = plan_checkin.get_current_checkin(db, user)
        if current is None:
            current = plan_checkin.start_new_series(db, user, plan)
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(400, str(exc)) from exc
    res["current_checkin"] = plan_checkin.checkin_to_dict(current)
    return res


@router.post("/generate", status_code=202)
def generate_plan(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Sinh thực đơn bằng LLM dựa trên profile + bệnh nền + dị ứng + calo mục tiêu."""
    _require_complete_profile_for_plan(db, user)

    job = plan_jobs.enqueue(user.id)
    return {"job_id": job.id, "status": job.status}


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
            "next_checkin": plan_checkin.checkin_to_dict(next_period),
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

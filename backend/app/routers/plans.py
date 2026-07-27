from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.deps import get_db, get_current_user, require_role
from app.models import User, NutritionPlan, PlanEvaluation
from app.services import plan_evaluator, plan_generator

router = APIRouter(prefix="/plans", tags=["plans"])


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

    res = plan_generator.plan_to_dict(plan, user)
    # Đủ 7 ngày → frontend hiện nút "Đánh giá & cập nhật lộ trình"
    res["days_elapsed"] = (date.today() - plan.start_date).days
    res["needs_evaluation"] = plan_evaluator.is_due(plan.start_date) and not \
        plan_evaluator.already_evaluated(db, plan.id, plan.start_date)

    last_eval = (
        db.query(PlanEvaluation)
        .join(NutritionPlan, NutritionPlan.id == PlanEvaluation.plan_id)  # type: ignore
        .filter(NutritionPlan.user_id == user.id)  # type: ignore
        .order_by(PlanEvaluation.evaluated_at.desc())
        .first()
    )
    res["last_evaluation"] = plan_evaluator.evaluation_to_dict(last_eval) if last_eval else None
    return res


@router.post("/generate")
def generate_plan(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Sinh thực đơn bằng LLM dựa trên profile + bệnh nền + dị ứng + calo mục tiêu."""
    if not user.profile:
        raise HTTPException(400, "Chưa có hồ sơ sức khỏe")

    plan = plan_generator.create_plan(db, user)
    db.commit()
    db.refresh(plan)
    return plan_generator.plan_to_dict(plan, user)


@router.post("/evaluate")
def evaluate_plan(
    force: bool = Query(False, description="Chấm ngay dù chưa đủ 7 ngày (dùng để demo)"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Chạy job đánh giá chu kỳ 7 ngày cho chính người dùng đang đăng nhập."""
    if not user.profile:
        raise HTTPException(400, "Chưa có hồ sơ sức khỏe")

    try:
        res = plan_evaluator.run_plan_job(db, user, force=force)
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Lỗi khi đánh giá lộ trình: {e}")

    if not res["evaluated"]:
        return {"evaluated": False, "reason": res["reason"]}

    return {
        "evaluated": True,
        "evaluation": plan_evaluator.evaluation_to_dict(res["evaluation"]),
        "plan": plan_generator.plan_to_dict(res["plan"], user),
    }


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



@router.post("/jobs/evaluate-all")
def evaluate_all(
    db: Session = Depends(get_db),
    _: User = Depends(require_role("ADMIN")),
):
    """Chạy job đánh giá cho toàn bộ người dùng có lộ trình đã đủ 7 ngày."""
    return plan_evaluator.run_job_for_all(db)

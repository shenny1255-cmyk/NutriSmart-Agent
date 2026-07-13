from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.deps import get_db, get_current_user
from app.models import User, NutritionPlan

router = APIRouter(prefix="/plans", tags=["plans"])


@router.get("/active")
def active_plan(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    plan = (
        db.query(NutritionPlan)
        .filter(NutritionPlan.user_id == user.id, NutritionPlan.status == "ACTIVE")
        .order_by(NutritionPlan.version.desc())
        .first()
    )
    if not plan:
        raise HTTPException(404, "Chưa có lộ trình nào")
    return plan


@router.post("/generate")
def generate_plan(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """TODO: thay bằng LLM sinh thực đơn dựa trên profile + bệnh nền + dị ứng."""
    profile = user.profile
    if not profile:
        raise HTTPException(400, "Chưa có hồ sơ sức khỏe")

    target = profile.daily_calorie_target or 2000

    # Nội dung giả để frontend render được — sẽ thay bằng output của LLM
    content = {
        "days": [
            {
                "meals": [
                    {"type": "Sáng", "name": "Phở bò", "kcal": int(target * 0.3)},
                    {"type": "Trưa", "name": "Cơm gà + rau luộc", "kcal": int(target * 0.4)},
                    {"type": "Tối", "name": "Salad ức gà", "kcal": int(target * 0.3)},
                ],
                "exercise": "Đi bộ 30 phút",
            }
            for _ in range(7)
        ]
    }

    # Hạ plan cũ xuống REVISED
    old = (
        db.query(NutritionPlan)
        .filter(NutritionPlan.user_id == user.id, NutritionPlan.status == "ACTIVE")
        .order_by(NutritionPlan.version.desc())
        .first()
    )
    if old:
        old.status = "REVISED"

    plan = NutritionPlan(
        user_id=user.id,
        version=(old.version + 1) if old else 1,
        parent_plan_id=old.id if old else None,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=7),
        daily_kcal_target=target,
        goal=profile.goal,
        content=content,
        generated_by="stub-v0",
        status="ACTIVE",
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan
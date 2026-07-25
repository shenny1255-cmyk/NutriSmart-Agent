from datetime import date, timedelta
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.deps import get_db, get_current_user
from app.models import User, ActivityLog
from app.schemas import DailySummaryOut, ActivityIn, TodayActivityOut

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tracking", tags=["tracking"])


@router.get("/summary", response_model=list[DailySummaryOut])
def summary(
    days: int = 7,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    sql = text("""
        SELECT day, kcal_intake, kcal_burned,
               daily_calorie_target, kcal_remaining
        FROM v_daily_summary
        WHERE user_id = :uid AND day >= :since
        ORDER BY day
    """)
    since = date.today() - timedelta(days=days - 1)
    rows = db.execute(sql, {"uid": str(user.id), "since": since}).mappings().all()
    return list(rows)


@router.post("/daily-activity", response_model=TodayActivityOut)
def upsert_daily_activity(
    payload: ActivityIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Mobile gửi số bước + calo tiêu hao lên. UPSERT theo (user_id, log_date)."""
    try:
        log_date = payload.log_date or date.today()

        # Tìm bản ghi hiện có cho ngày hôm đó (exercise_id IS NULL -> log từ Mobile)
        existing = (
            db.query(ActivityLog)
            .filter(
                ActivityLog.user_id == user.id,
                ActivityLog.log_date == log_date,
                ActivityLog.exercise_id.is_(None)
            )
            .first()
        )

        if existing:
            existing.steps = payload.steps
            existing.calories_burned = payload.calories_burned
        else:
            existing = ActivityLog(
                user_id=user.id,
                steps=payload.steps,
                calories_burned=payload.calories_burned,
                log_date=log_date,
            )
            db.add(existing)

        db.commit()
        db.refresh(existing)

        return TodayActivityOut(
            steps=existing.steps or 0,
            calories_burned=float(existing.calories_burned or 0),
            distance_km=payload.distance_km,
            log_date=existing.log_date,
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Lỗi upsert_daily_activity: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/today-activity", response_model=TodayActivityOut)
def get_today_activity(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Web Dashboard gọi để lấy số bước + calo tiêu hao hôm nay từ Mobile."""
    today = date.today()
    log = (
        db.query(ActivityLog)
        .filter(
            ActivityLog.user_id == user.id,
            ActivityLog.log_date == today,
            ActivityLog.exercise_id.is_(None)
        )
        .first()
    )

    return TodayActivityOut(
        steps=log.steps if log else 0,
        calories_burned=float(log.calories_burned) if log else 0.0,
        distance_km=0.0,
        log_date=today,
    )
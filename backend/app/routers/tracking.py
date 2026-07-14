from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.deps import get_db, get_current_user
from app.models import User
from app.schemas import DailySummaryOut

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
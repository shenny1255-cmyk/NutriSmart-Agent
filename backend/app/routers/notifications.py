from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.deps import get_current_user, get_db
from app.models import Notification, User
from app.schemas import NotificationOut

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationOut])
def list_notifications(
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return (
        db.query(Notification)
        .filter(Notification.user_id == user.id)  # type: ignore
        .order_by(Notification.created_at.desc())  # type: ignore
        .limit(limit)
        .all()
    )


@router.put("/{notification_id}/read", response_model=NotificationOut)
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    row = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == user.id,  # type: ignore
    ).first()
    if not row:
        raise HTTPException(404, "Không tìm thấy thông báo")
    row.is_read = True  # type: ignore
    db.commit()
    db.refresh(row)
    return row

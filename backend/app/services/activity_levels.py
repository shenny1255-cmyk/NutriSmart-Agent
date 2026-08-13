from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import ActivityLevel


def get_activity_level(db: Session, level_id: int) -> ActivityLevel:
    """Lấy mức vận động hợp lệ để dùng chung hệ số từ CSDL."""
    level = db.get(ActivityLevel, level_id)
    if level is None:
        raise HTTPException(422, "Mức độ vận động không hợp lệ")
    return level

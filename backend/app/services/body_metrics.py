from datetime import date

from sqlalchemy.orm import Session

from app.models import BodyMetricHistory


def latest_body_metric(db: Session, user_id) -> BodyMetricHistory | None:
    """Lấy số đo mới nhất của người dùng."""
    return (
        db.query(BodyMetricHistory)
        .filter(BodyMetricHistory.user_id == user_id)  # type: ignore
        .order_by(BodyMetricHistory.recorded_at.desc(), BodyMetricHistory.id.desc())  # type: ignore
        .first()
    )


def upsert_body_metric(
    db: Session,
    user_id,
    *,
    height_cm: float | None = None,
    weight_kg: float | None = None,
    recorded_at: date | None = None,
) -> BodyMetricHistory:
    """Ghi số đo trong ngày, kế thừa giá trị còn thiếu từ mốc gần nhất."""
    metric_date = recorded_at or date.today()
    row = (
        db.query(BodyMetricHistory)
        .filter(
            BodyMetricHistory.user_id == user_id,  # type: ignore
            BodyMetricHistory.recorded_at == metric_date,  # type: ignore
        )
        .first()
    )
    latest = latest_body_metric(db, user_id)
    resolved_height = height_cm if height_cm is not None else (
        float(latest.height_cm) if latest and latest.height_cm is not None else None
    )
    resolved_weight = weight_kg if weight_kg is not None else (
        float(latest.weight_kg) if latest and latest.weight_kg is not None else None
    )

    if row:
        if height_cm is not None:
            row.height_cm = height_cm  # type: ignore
        elif row.height_cm is None:
            row.height_cm = resolved_height  # type: ignore
        if weight_kg is not None:
            row.weight_kg = weight_kg  # type: ignore
        elif row.weight_kg is None:
            row.weight_kg = resolved_weight  # type: ignore
        return row

    row = BodyMetricHistory(
        user_id=user_id,
        recorded_at=metric_date,
        height_cm=resolved_height,
        weight_kg=resolved_weight,
    )
    db.add(row)
    return row

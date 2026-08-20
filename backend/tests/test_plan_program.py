from datetime import date
from datetime import timedelta
import uuid

import pytest
from pydantic import ValidationError
from sqlalchemy import text

from app.database import SessionLocal, engine
from app.schemas import PlanGenerateIn
from app.services.plan_checkin import program_end_date, total_program_periods


@pytest.mark.parametrize(
    ("months", "expected_days", "expected_periods"),
    [
        (1, 28, 2),
        (3, 84, 6),
        (12, 336, 24),
    ],
)
def test_thoi_han_chuong_trinh_dung_block_bon_tuan(months, expected_days, expected_periods):
    start = date(2026, 8, 20)

    assert (program_end_date(start, months) - start).days + 1 == expected_days
    assert total_program_periods(months) == expected_periods


@pytest.mark.parametrize("months", [0, 13])
def test_schema_tu_choi_thoi_han_ngoai_mot_den_muoi_hai_thang(months):
    with pytest.raises(ValidationError):
        PlanGenerateIn(height_cm=170, weight_kg=70, duration_months=months)


def test_schema_tao_chuong_trinh_mac_dinh_ba_thang():
    payload = PlanGenerateIn(height_cm=170, weight_kg=70)

    assert payload.duration_months == 3
    assert payload.confirm_recreate is False
    assert payload.expected_active_plan_id is None


def _program_schema_up() -> bool:
    try:
        with engine.connect() as connection:
            return bool(connection.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'plan_checkin_series'
                      AND column_name = 'duration_months'
                )
            """)).scalar())
    except Exception:
        return False


@pytest.mark.skipif(not _program_schema_up(), reason="Cần PostgreSQL đã áp dụng migration 27")
def test_khong_tao_dot_sau_khi_het_thoi_han_chuong_trinh():
    from app.models import BodyMetricHistory, NutritionPlan, PlanCheckinSeries, User, UserProfile
    from app.services.plan_checkin import (
        create_next_period, extend_program, program_summary, start_new_series,
    )

    db = SessionLocal()
    user = User(email=f"program-{uuid.uuid4().hex[:8]}@test.local", password_hash="x", role="USER")
    db.add(user)
    db.flush()
    db.add(UserProfile(
        user_id=user.id, full_name="Người kiểm thử", gender="MALE",
        birth_date=date(2000, 1, 1), activity_level=3,
        goal="MAINTAIN", daily_calorie_target=2000,
    ))
    db.add(BodyMetricHistory(user_id=user.id, height_cm=170, weight_kg=70))
    plan = NutritionPlan(
        user_id=user.id, version=1, start_date=date.today(), end_date=date.today(),
        daily_kcal_target=2000, goal="MAINTAIN", content={"days": []}, status="ACTIVE",
    )
    db.add(plan)
    db.flush()

    first = start_new_series(db, user, plan, today=date.today(), duration_months=1)
    first.status = "COMPLETED"  # type: ignore
    first.actual_weight_kg = 70  # type: ignore
    db.flush()
    second = create_next_period(db, user, first, plan, today=date.today() + timedelta(days=14))
    assert second is not None
    series = db.query(PlanCheckinSeries).filter(PlanCheckinSeries.id == second.series_id).one()  # type: ignore
    assert series.duration_months == 1
    assert second.period_number == 2
    second.status = "COMPLETED"  # type: ignore
    second.actual_weight_kg = 70  # type: ignore
    db.flush()

    assert create_next_period(db, user, second, plan, today=date.today() + timedelta(days=28)) is None
    db.flush()
    assert second.period_number == 2
    assert second.series_id is not None
    assert plan.status == "COMPLETED"
    assert plan.end_date == date.today() + timedelta(days=27)

    summary = program_summary(db, user, series)
    assert summary["start_weight_kg"] == 70
    assert summary["end_weight_kg"] == 70
    assert summary["total_periods"] == 2
    assert len(summary["checkins"]) == 2

    extended, third = extend_program(
        db, user, additional_months=1, today=date.today() + timedelta(days=28)
    )
    assert extended.id == series.id
    assert extended.duration_months == 2
    assert extended.status == "ACTIVE"
    assert extended.planned_end_date == date.today() + timedelta(days=55)
    assert plan.status == "ACTIVE"
    assert third.period_number == 3

    db.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": str(user.id)})
    db.commit()
    db.close()

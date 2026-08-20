from datetime import date, timedelta
import uuid
from typing import Any, cast

import pytest
from pydantic import ValidationError
from sqlalchemy import text

from app.database import SessionLocal, engine
from app.schemas import PlanProgressIn


def test_schema_progress_chi_nhan_bon_item_key_on_dinh():
    assert PlanProgressIn(checked_items=["meal:0", "exercise"]).checked_items == ["meal:0", "exercise"]

    with pytest.raises(ValidationError):
        PlanProgressIn(checked_items=cast(Any, ["meal:9"]))
    with pytest.raises(ValidationError):
        PlanProgressIn(checked_items=["meal:0", "meal:0"])


def _progress_schema_up() -> bool:
    try:
        with engine.connect() as connection:
            return bool(connection.execute(text("SELECT to_regclass('plan_daily_progress')")).scalar())
    except Exception:
        return False


def _create_program(
    db,
    *,
    started_at: date | None = None,
    exercise_data: Any | None = None,
):
    from app.models import BodyMetricHistory, NutritionPlan, User, UserProfile
    from app.services.plan_checkin import start_new_series

    user = User(email=f"progress-{uuid.uuid4().hex[:8]}@test.local", password_hash="x", role="USER")
    db.add(user)
    db.flush()
    db.add(UserProfile(
        user_id=user.id, full_name="Người theo dõi", gender="MALE",
        birth_date=date(2000, 1, 1), activity_level=3,
        goal="MAINTAIN", daily_calorie_target=2000,
    ))
    db.add(BodyMetricHistory(user_id=user.id, height_cm=170, weight_kg=70))
    started_at = started_at or date.today()
    plan = NutritionPlan(
        user_id=user.id,
        version=1,
        start_date=started_at,
        end_date=started_at,
        daily_kcal_target=2000,
        goal="MAINTAIN",
        content={
            "days": [
                {
                    "meals": [
                        {"type": "Sáng", "name": "Phở bò", "kcal": 450},
                        {"type": "Trưa", "name": "Cơm gà", "kcal": 700},
                        {"type": "Tối", "name": "Salad", "kcal": 500},
                    ],
                    "exercise": exercise_data if exercise_data is not None else {
                        "name": "Đi bộ", "duration_min": 30, "calories_kcal": 180,
                    },
                }
                for _ in range(7)
            ]
        },
        status="ACTIVE",
    )
    db.add(plan)
    db.flush()
    checkin = start_new_series(db, user, plan, today=started_at, duration_months=1)
    db.commit()
    return user, plan, checkin


def test_doc_duoc_van_dong_dang_chuoi_cua_plan_cu():
    from app.services.plan_progress import _exercise_data

    assert _exercise_data({"exercise": "Yoga - 30 phút - đốt 200 kcal"}) == (
        "Yoga", 30, 200.0,
    )


@pytest.mark.skipif(not _progress_schema_up(), reason="Cần PostgreSQL đã áp dụng migration 27")
def test_luu_progress_lap_lai_khong_nhan_doi_nhat_ky_va_dat_lai_khong_xoa_log_tay():
    from app.models import ActivityLog, MealLog
    from app.routers.tracking import get_today_activity, upsert_daily_activity
    from app.schemas import ActivityIn
    from app.services.plan_progress import reset_progress, save_progress

    db = SessionLocal()
    user, plan, _ = _create_program(db)
    manual = MealLog(
        user_id=user.id,
        meal_type="SNACK",
        quantity=1,
        calories_kcal=100,
        log_date=date.today(),
        source_type="MANUAL",
        item_name_snapshot="Sữa chua",
    )
    db.add(manual)
    db.commit()

    first = save_progress(
        db, user, plan.id, date.today(), ["meal:0", "exercise"], today=date.today()
    )
    db.commit()
    assert first["kcal_intake_delta"] == 450
    assert first["kcal_burned_delta"] == 180

    second = save_progress(
        db, user, plan.id, date.today(), ["meal:0", "exercise"], today=date.today()
    )
    db.commit()
    assert second["kcal_intake_delta"] == 0
    assert second["kcal_burned_delta"] == 0
    assert db.query(MealLog).filter(
        MealLog.user_id == user.id,  # type: ignore[arg-type]
        MealLog.source_type == "PLAN",  # type: ignore[arg-type]
    ).count() == 1
    assert db.query(ActivityLog).filter(
        ActivityLog.user_id == user.id,  # type: ignore[arg-type]
        ActivityLog.source_type == "PLAN",  # type: ignore[arg-type]
    ).count() == 1

    upsert_daily_activity(
        ActivityIn(steps=4321, calories_burned=210, log_date=date.today()), db, user
    )
    assert db.query(ActivityLog).filter(
        ActivityLog.user_id == user.id,  # type: ignore[arg-type]
        ActivityLog.source_type == "PLAN",  # type: ignore[arg-type]
    ).count() == 1
    assert db.query(ActivityLog).filter(
        ActivityLog.user_id == user.id,  # type: ignore[arg-type]
        ActivityLog.source_type == "MOBILE",  # type: ignore[arg-type]
    ).count() == 1
    assert get_today_activity(db, user).steps == 4321

    reset = reset_progress(db, user, plan.id, date.today(), today=date.today())
    db.commit()
    assert reset["checked_items"] == []
    assert db.query(MealLog).filter(
        MealLog.user_id == user.id,  # type: ignore[arg-type]
        MealLog.source_type == "PLAN",  # type: ignore[arg-type]
    ).count() == 0
    assert db.query(ActivityLog).filter(
        ActivityLog.user_id == user.id,  # type: ignore[arg-type]
        ActivityLog.source_type == "PLAN",  # type: ignore[arg-type]
    ).count() == 0
    assert db.query(ActivityLog).filter(
        ActivityLog.user_id == user.id,  # type: ignore[arg-type]
        ActivityLog.source_type == "MOBILE",  # type: ignore[arg-type]
    ).count() == 1
    assert db.query(MealLog).filter(MealLog.id == manual.id).count() == 1  # type: ignore

    db.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": str(user.id)})
    db.commit()
    db.close()


@pytest.mark.skipif(not _progress_schema_up(), reason="Cần PostgreSQL đã áp dụng migration 27")
def test_ghi_nhan_ngay_va_khoa_cap_nhat_tuong_lai():
    from app.services.plan_progress import complete_progress, reset_progress

    db = SessionLocal()
    user, plan, _ = _create_program(db)

    result = complete_progress(
        db,
        user,
        plan.id,
        date.today(),
        ["meal:0", "meal:1", "meal:2", "exercise"],
        today=date.today(),
    )
    db.commit()
    assert result["status"] == "COMPLETED"
    assert result["kcal_intake_delta"] == 1650
    assert result["kcal_burned_delta"] == 180

    reset = reset_progress(db, user, plan.id, date.today(), today=date.today())
    db.commit()
    assert reset["status"] == "IN_PROGRESS"
    assert reset["checked_items"] == []

    with pytest.raises(ValueError, match="tương lai"):
        complete_progress(
            db, user, plan.id, date.today() + timedelta(days=1), [], today=date.today()
        )
    db.rollback()

    db.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": str(user.id)})
    db.commit()
    db.close()


@pytest.mark.skipif(not _progress_schema_up(), reason="Cần PostgreSQL đã áp dụng migration 27")
def test_ngay_da_ghi_nhan_van_sua_duoc_den_khi_dot_dong():
    from app.models import PlanDailyProgress
    from app.services.plan_progress import complete_progress, reset_progress, save_progress

    db = SessionLocal()
    started_at = date.today() - timedelta(days=2)
    progress_date = date.today() - timedelta(days=1)
    user, plan, checkin = _create_program(db, started_at=started_at)

    recorded = complete_progress(
        db, user, plan.id, progress_date, ["meal:0"], today=date.today()
    )
    db.commit()
    assert recorded["status"] == "COMPLETED"

    updated = save_progress(
        db, user, plan.id, progress_date, ["meal:1", "exercise"], today=date.today()
    )
    db.commit()
    assert updated["status"] == "COMPLETED"
    assert updated["checked_items"] == ["meal:1", "exercise"]

    reset = reset_progress(db, user, plan.id, progress_date, today=date.today())
    db.commit()
    assert reset["status"] == "IN_PROGRESS"
    assert reset["checked_items"] == []
    row = db.query(PlanDailyProgress).filter(PlanDailyProgress.id == reset["id"]).one()  # type: ignore
    assert row.completed_at is None

    checkin.status = "COMPLETED"  # type: ignore
    db.commit()
    with pytest.raises(RuntimeError, match="đã khóa"):
        save_progress(db, user, plan.id, progress_date, ["meal:0"], today=date.today())
    db.rollback()

    db.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": str(user.id)})
    db.commit()
    db.close()


@pytest.mark.skipif(not _progress_schema_up(), reason="Cần PostgreSQL đã áp dụng migration 27")
def test_luu_lai_tu_sua_log_zero_cua_van_dong_plan_cu():
    from app.models import ActivityLog
    from app.services.plan_progress import save_progress

    db = SessionLocal()
    legacy_exercise = "Yoga - 30 phút - đốt 200 kcal"
    user, plan, _ = _create_program(db, exercise_data=legacy_exercise)

    save_progress(db, user, plan.id, date.today(), ["exercise"], today=date.today())
    db.commit()
    activity = db.query(ActivityLog).filter(
        ActivityLog.user_id == user.id,  # type: ignore[arg-type]
        ActivityLog.source_type == "PLAN",  # type: ignore[arg-type]
    ).one()
    activity.duration_min = 0  # type: ignore
    activity.calories_burned = 0  # type: ignore
    activity.item_name_snapshot = legacy_exercise  # type: ignore
    db.commit()

    repaired = save_progress(
        db, user, plan.id, date.today(), ["exercise"], today=date.today()
    )
    db.commit()
    db.refresh(activity)
    assert repaired["kcal_burned_delta"] == 200
    assert activity.duration_min == 30
    assert float(activity.calories_burned) == 200
    assert activity.item_name_snapshot == "Yoga"

    db.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": str(user.id)})
    db.commit()
    db.close()

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
    ).count() == 0
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


@pytest.mark.skipif(not _progress_schema_up(), reason="Cần PostgreSQL đã áp dụng migration 27")
def test_mobile_chi_tu_tick_khi_dat_nguong_va_dong_bo_lap_khong_cong_trung():
    from app.models import ActivityLog, PlanDailyProgress
    from app.routers.tracking import (
        danh_sach_van_dong,
        get_today_activity,
        summary,
        upsert_daily_activity,
    )
    from app.schemas import ActivityIn
    from app.services.plan_progress import save_progress

    db = SessionLocal()
    user, plan, _ = _create_program(
        db,
        exercise_data={"name": "Yoga", "duration_min": 30, "calories_kcal": 300},
    )

    initial = get_today_activity(db, user)
    assert initial.plan_exercise is not None
    assert initial.plan_exercise.required_kcal == 350
    assert initial.plan_exercise.actual_kcal == 0

    below = upsert_daily_activity(
        ActivityIn(steps=7000, calories_burned=9999, log_date=date.today()), db, user
    )
    assert below.calories_burned == pytest.approx(326.7)
    assert below.plan_exercise is not None
    assert below.plan_exercise.required_kcal == 350
    assert below.plan_exercise.remaining_kcal == pytest.approx(23.3)
    assert below.plan_exercise.checked is False
    assert below.plan_exercise.auto_checked is False
    assert below.plan_exercise.reason == "BELOW_TARGET"
    assert db.query(PlanDailyProgress).filter(
        PlanDailyProgress.user_id == user.id  # type: ignore[arg-type]
    ).count() == 0

    reached = upsert_daily_activity(
        ActivityIn(steps=8000, calories_burned=9999, log_date=date.today()), db, user
    )
    assert reached.calories_burned == pytest.approx(373.3)
    assert reached.plan_exercise is not None
    assert reached.plan_exercise.checked is True
    assert reached.plan_exercise.auto_checked is True
    assert reached.plan_exercise.source == "MOBILE"
    assert reached.plan_exercise.reason == "AUTO_CHECKED"

    repeated = upsert_daily_activity(
        ActivityIn(steps=9000, calories_burned=0, log_date=date.today()), db, user
    )
    assert repeated.calories_burned == pytest.approx(420)
    assert repeated.plan_exercise is not None
    assert repeated.plan_exercise.checked is True
    assert repeated.plan_exercise.auto_checked is False
    assert repeated.plan_exercise.reason == "ALREADY_CHECKED"

    progress = db.query(PlanDailyProgress).filter(
        PlanDailyProgress.user_id == user.id  # type: ignore[arg-type]
    ).one()
    assert cast(list[str], progress.checked_items) == ["exercise"]
    assert db.query(ActivityLog).filter(
        ActivityLog.user_id == user.id,  # type: ignore[arg-type]
        ActivityLog.source_type == "MOBILE",  # type: ignore[arg-type]
    ).count() == 1
    assert db.query(ActivityLog).filter(
        ActivityLog.user_id == user.id,  # type: ignore[arg-type]
        ActivityLog.source_type == "PLAN",  # type: ignore[arg-type]
    ).count() == 0

    save_progress(
        db, user, plan.id, date.today(), ["meal:0", "exercise"], today=date.today()
    )
    db.commit()
    assert db.query(ActivityLog).filter(
        ActivityLog.user_id == user.id,  # type: ignore[arg-type]
        ActivityLog.source_type == "PLAN",  # type: ignore[arg-type]
    ).count() == 0
    activities = danh_sach_van_dong(db, user, date.today())
    assert len(activities) == 1
    assert activities[0].source_type == "MOBILE"
    assert activities[0].calories_burned == pytest.approx(420)
    assert summary(days=1, db=db, user=user)[-1]["kcal_burned"] == pytest.approx(420)

    db.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": str(user.id)})
    db.commit()
    db.close()


@pytest.mark.skipif(not _progress_schema_up(), reason="Cần PostgreSQL đã áp dụng migration 27")
def test_mobile_van_luu_nhat_ky_nhung_khong_tick_khi_dot_da_khoa():
    from app.models import ActivityLog, PlanDailyProgress
    from app.routers.tracking import upsert_daily_activity
    from app.schemas import ActivityIn

    db = SessionLocal()
    user, _, checkin = _create_program(
        db,
        exercise_data={"name": "Chạy bộ", "duration_min": 30, "calories_kcal": 300},
    )
    checkin.status = "COMPLETED"  # type: ignore
    db.commit()

    result = upsert_daily_activity(
        ActivityIn(steps=9000, calories_burned=0, log_date=date.today()), db, user
    )
    assert result.plan_exercise is not None
    assert result.plan_exercise.eligible is False
    assert result.plan_exercise.reason == "CHECKIN_CLOSED"
    assert result.plan_exercise.checked is False
    assert db.query(ActivityLog).filter(
        ActivityLog.user_id == user.id,  # type: ignore[arg-type]
        ActivityLog.source_type == "MOBILE",  # type: ignore[arg-type]
    ).count() == 1
    assert db.query(PlanDailyProgress).filter(
        PlanDailyProgress.user_id == user.id  # type: ignore[arg-type]
    ).count() == 0

    db.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": str(user.id)})
    db.commit()
    db.close()


@pytest.mark.skipif(not _progress_schema_up(), reason="Cần PostgreSQL đã áp dụng migration 27")
def test_mobile_thay_log_uoc_tinh_web_va_reset_chi_bo_lien_ket():
    from app.models import ActivityLog, PlanDailyProgress
    from app.routers.tracking import upsert_daily_activity
    from app.schemas import ActivityIn
    from app.services.plan_progress import reset_progress, save_progress

    db = SessionLocal()
    user, plan, _ = _create_program(
        db,
        exercise_data={"name": "Yoga", "duration_min": 30, "calories_kcal": 300},
    )
    save_progress(db, user, plan.id, date.today(), ["exercise"], today=date.today())
    db.commit()
    assert db.query(ActivityLog).filter(
        ActivityLog.user_id == user.id,  # type: ignore[arg-type]
        ActivityLog.source_type == "PLAN",  # type: ignore[arg-type]
    ).count() == 1

    synced = upsert_daily_activity(
        ActivityIn(steps=8000, calories_burned=373.3, log_date=date.today()), db, user
    )
    assert synced.plan_exercise is not None
    assert synced.plan_exercise.checked is True
    assert synced.plan_exercise.auto_checked is False
    assert db.query(ActivityLog).filter(
        ActivityLog.user_id == user.id,  # type: ignore[arg-type]
        ActivityLog.source_type == "PLAN",  # type: ignore[arg-type]
    ).count() == 0
    mobile = db.query(ActivityLog).filter(
        ActivityLog.user_id == user.id,  # type: ignore[arg-type]
        ActivityLog.source_type == "MOBILE",  # type: ignore[arg-type]
    ).one()
    assert mobile.source_item_key == "exercise"
    assert cast(Any, mobile.source_progress_id) is not None

    reset_progress(db, user, plan.id, date.today(), today=date.today())
    db.commit()
    db.refresh(mobile)
    progress = db.query(PlanDailyProgress).filter(
        PlanDailyProgress.user_id == user.id  # type: ignore[arg-type]
    ).one()
    assert cast(list[str], progress.checked_items) == []
    assert cast(Any, mobile.source_progress_id) is None
    assert mobile.source_item_key is None
    assert db.query(ActivityLog).filter(ActivityLog.id == mobile.id).count() == 1  # type: ignore[arg-type]

    resynced = upsert_daily_activity(
        ActivityIn(steps=8000, calories_burned=373.3, log_date=date.today()), db, user
    )
    assert resynced.plan_exercise is not None
    assert resynced.plan_exercise.auto_checked is True
    db.refresh(progress)
    assert cast(list[str], progress.checked_items) == ["exercise"]

    db.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": str(user.id)})
    db.commit()
    db.close()


@pytest.mark.skipif(not _progress_schema_up(), reason="Cần PostgreSQL đã áp dụng migration 27")
def test_bai_tap_plan_thieu_kcal_tu_dong_tinh_met_va_sua_log_zero():
    from app.models import ActivityLog
    from app.routers.tracking import danh_sach_van_dong, summary
    from app.services.plan_progress import save_progress

    db = SessionLocal()
    # Plan chỉ có chuỗi "Đi bộ 30 phút" (không có chữ kcal)
    user, plan, _ = _create_program(db, exercise_data="Đi bộ 30 phút")

    result = save_progress(db, user, plan.id, date.today(), ["exercise"], today=date.today())
    db.commit()

    # User nặng 60kg, đi bộ 30 phút theo MET -> > 0 kcal
    assert result["kcal_burned_delta"] > 0
    activity = db.query(ActivityLog).filter(
        ActivityLog.user_id == user.id,  # type: ignore[arg-type]
        ActivityLog.source_type == "PLAN",  # type: ignore[arg-type]
    ).one()
    assert float(activity.calories_burned or 0) > 0
    assert activity.duration_min == 30

    # Giả lập bản ghi cũ bị 0 kcal và kiểm tra danh_sach_van_dong / summary tự sửa
    activity.calories_burned = 0  # type: ignore
    db.commit()

    acts = danh_sach_van_dong(db, user, date.today())
    assert acts[0].calories_burned > 0
    db.refresh(activity)
    assert float(activity.calories_burned or 0) > 0

    activity.calories_burned = 0  # type: ignore
    db.commit()
    sums = summary(days=1, db=db, user=user)
    assert sums[-1]["kcal_burned"] > 0

    db.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": str(user.id)})
    db.commit()
    db.close()


@pytest.mark.skipif(not _progress_schema_up(), reason="Cần PostgreSQL đã áp dụng migration 27")
def test_meal_log_sync_auto_checks_plan_meal_slot():
    from app.models import MealLog, PlanDailyProgress
    from app.routers.vision import log_meal
    from app.schemas import MealLogIn
    from app.services.plan_progress import save_progress

    db = SessionLocal()
    user, plan, _ = _create_program(db)

    # 1. Log bữa sáng qua Vision
    payload = MealLogIn(
        food_name="Phở bò đặc biệt",
        calories_kcal=520,
        protein_g=25,
        carb_g=60,
        fat_g=15,
        meal_type="BREAKFAST",
        quantity=1,
        log_date=date.today(),
    )
    res = log_meal(payload, db=db, user=user)
    assert res["status"] == "success"
    assert res["plan_synced"] is not None
    assert res["plan_synced"]["item_key"] == "meal:0"
    assert res["plan_synced"]["auto_checked"] is True

    # 2. Kiểm tra PlanDailyProgress đã được tick "meal:0"
    progress = db.query(PlanDailyProgress).filter(
        PlanDailyProgress.user_id == user.id,
        PlanDailyProgress.progress_date == date.today(),  # type: ignore[arg-type]
    ).first()
    assert progress is not None
    assert "meal:0" in (progress.checked_items or [])

    # 3. Kiểm tra không bị nhân đôi calo (chỉ có 1 MealLog bữa sáng do VISION tạo ra)
    breakfast_logs = db.query(MealLog).filter(
        MealLog.user_id == user.id,
        MealLog.log_date == date.today(),  # type: ignore[arg-type]
        MealLog.meal_type == "BREAKFAST",
    ).all()
    assert len(breakfast_logs) == 1
    assert breakfast_logs[0].source_type == "VISION"
    assert breakfast_logs[0].calories_kcal == 520

    # 4. Khi người dùng bỏ tick "meal:0" trên Lộ trình
    save_progress(db, user, plan.id, date.today(), [], today=date.today())
    db.commit()
    db.refresh(progress)
    assert progress.checked_items == []
    # Bản ghi trong Nhật ký vẫn còn nguyên, chỉ gỡ liên kết
    db.refresh(breakfast_logs[0])
    assert breakfast_logs[0].source_progress_id is None

    db.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": str(user.id)})
    db.commit()
    db.close()


@pytest.mark.skipif(not _progress_schema_up(), reason="Cần PostgreSQL đã áp dụng migration 27")
def test_ghi_mon_thu_cong_bao_da_dong_bo_va_lo_trinh_biet_bua_tu_nhat_ky():
    from app.routers.tracking import them_bua_an
    from app.schemas import ManualMealIn
    from app.services.plan_progress import list_progress

    db = SessionLocal()
    user, plan, checkin = _create_program(db)
    try:
        sang = them_bua_an(db, user, ManualMealIn(
            food_name="Bánh mì trứng", calories_kcal=350, meal_type="BREAKFAST", log_date=date.today()))
        assert sang.plan_synced is True
        phu = them_bua_an(db, user, ManualMealIn(
            food_name="Sữa chua", calories_kcal=100, meal_type="SNACK", log_date=date.today()))
        assert phu.plan_synced is False          # bữa phụ không có ô trên lộ trình

        today = next(r for r in list_progress(db, user, checkin) if r["progress_date"] == date.today())
        assert "meal:0" in today["checked_items"] and today["diary_items"] == ["meal:0"]
    finally:
        db.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": str(user.id)})
        db.commit()
        db.close()


@pytest.mark.skipif(not _progress_schema_up(), reason="Cần PostgreSQL đã áp dụng migration 27")
def test_dong_bo_buoc_chan_nho_khong_lam_tut_kcal_bai_tap_tick_tay():
    """Kịch bản E: Tick tay bài tập 300 kcal, sau đó app gửi 1.000 bước (40 kcal) không bị ghi đè làm tụt kcal."""
    from app.models import ActivityLog
    from app.routers.tracking import upsert_daily_activity
    from app.schemas import ActivityIn
    from app.services.plan_progress import save_progress

    db = SessionLocal()
    user, plan, _ = _create_program(
        db,
        exercise_data={"name": "Yoga", "duration_min": 30, "calories_kcal": 300},
    )
    try:
        # Tick tay trên Web
        save_progress(db, user, plan.id, date.today(), ["exercise"], today=date.today())
        db.commit()

        # Kiểm tra có 1 log PLAN 300 kcal
        plan_log = db.query(ActivityLog).filter(
            ActivityLog.user_id == user.id,
            ActivityLog.source_type == "PLAN",
        ).one()
        assert float(plan_log.calories_burned or 0) == 300.0

        # App gửi 1.000 bước (~46.7 kcal < 300 kcal)
        synced = upsert_daily_activity(
            ActivityIn(steps=1000, log_date=date.today()), db, user
        )
        assert synced.plan_exercise is not None
        assert synced.plan_exercise.checked is True

        # Tổng kcal tiêu hao trong ngày được BẢO TOÀN đúng 300 kcal (top-up: plan + mobile = 300 kcal)
        all_logs = db.query(ActivityLog).filter(ActivityLog.user_id == user.id).all()
        total_kcal = sum(float(log.calories_burned or 0) for log in all_logs)
        assert round(total_kcal, 1) == 300.0
    finally:
        db.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": str(user.id)})
        db.commit()
        db.close()


@pytest.mark.skipif(not _progress_schema_up(), reason="Cần PostgreSQL đã áp dụng migration 27")
def test_sua_buoc_chan_xuong_duoi_nguong_bo_tick_va_khong_cong_trung():
    """Kịch bản I: Gõ nhầm 50.000 bước (auto-check), rồi sửa lại 5.000 bước (< 350 kcal) thì bỏ tick và không cộng trùng."""
    from app.models import ActivityLog, PlanDailyProgress
    from app.routers.tracking import upsert_daily_activity
    from app.schemas import ActivityIn

    db = SessionLocal()
    user, plan, _ = _create_program(
        db,
        exercise_data={"name": "Đi bộ", "duration_min": 30, "calories_kcal": 300},
    )
    try:
        # Lần 1: gõ nhầm 50.000 bước -> auto-checked
        r1 = upsert_daily_activity(ActivityIn(steps=50000, log_date=date.today()), db, user)
        assert r1.plan_exercise is not None
        assert r1.plan_exercise.checked is True

        # Lần 2: sửa xuống 5.000 bước với replace=True
        r2 = upsert_daily_activity(ActivityIn(steps=5000, replace=True, log_date=date.today()), db, user)
        assert r2.steps == 5000
        assert r2.plan_exercise is not None
        assert r2.plan_exercise.checked is False
        assert r2.plan_exercise.reason == "BELOW_TARGET"

        # CSDL chỉ còn 1 log MOBILE duy nhất, KHÔNG sinh log PLAN cộng trùng
        all_activities = db.query(ActivityLog).filter(ActivityLog.user_id == user.id).all()
        assert len(all_activities) == 1
        assert all_activities[0].source_type == "MOBILE"
        assert all_activities[0].source_item_key is None
    finally:
        db.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": str(user.id)})
        db.commit()
        db.close()


@pytest.mark.skipif(not _progress_schema_up(), reason="Cần PostgreSQL đã áp dụng migration 27")
def test_dong_bo_buoc_chan_co_replace_cho_phep_sua_xuong():
    """Gửi 6.000 bước rồi gửi lại 2.000 bước với replace=True để sửa nhầm."""
    from app.models import ActivityLog
    from app.routers.tracking import upsert_daily_activity
    from app.schemas import ActivityIn

    db = SessionLocal()
    user, _, _ = _create_program(db)
    try:
        # Lần 1: gửi 6.000 bước
        r1 = upsert_daily_activity(ActivityIn(steps=6000, log_date=date.today()), db, user)
        assert r1.steps == 6000

        # Lần 2: sửa nhầm xuống 2.000 bước với replace=True
        r2 = upsert_daily_activity(ActivityIn(steps=2000, replace=True, log_date=date.today()), db, user)
        assert r2.steps == 2000

        log = db.query(ActivityLog).filter(
            ActivityLog.user_id == user.id,
            ActivityLog.source_type == "MOBILE",
        ).one()
        assert log.steps == 2000
    finally:
        db.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": str(user.id)})
        db.commit()
        db.close()


def test_resolve_exercise_data_khong_bi_attribute_error_khi_thieu_metric():
    """Bug c: User không có metric trong body_metrics_history không bị crash AttributeError."""
    from app.models import User, UserProfile
    from app.services.plan_progress import _resolve_exercise_data

    db = SessionLocal()
    user = User(email=f"test_nometric_{date.today()}@nutrismart.vn", password_hash="pw", role="USER")
    db.add(user)
    db.flush()
    profile = UserProfile(user_id=user.id, full_name="Test No Metric")
    db.add(profile)
    db.commit()
    try:
        # user.profile không có weight_kg, hàm phải tự fallback về 60.0 kg an toàn
        name, duration, kcal = _resolve_exercise_data(db, user, {"exercise": {"name": "Đi bộ vừa", "duration_min": 30, "calories_kcal": 0}})
        assert name == "Đi bộ vừa"
        assert duration == 30
        assert kcal > 0  # tính được kcal dựa trên 60kg fallback
    finally:
        db.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": str(user.id)})
        db.commit()
        db.close()

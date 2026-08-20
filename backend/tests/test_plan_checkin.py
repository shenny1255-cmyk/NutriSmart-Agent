from datetime import date, timedelta
from typing import Any
import uuid

import pytest
from pydantic import ValidationError
from sqlalchemy import text

from app.database import SessionLocal, engine
from app.schemas import CheckinSubmitIn
from app.services.plan_checkin import (
    derive_adherence,
    derive_data_quality,
    derive_outcome,
    derive_recommendation,
    derive_safety_flags,
    display_status,
    expected_weight_range,
    propose_kcal_target,
)


def test_trang_thai_hien_thi_duoc_suy_ra_tu_moc_ngay():
    start = date(2026, 8, 1)
    due = start + timedelta(days=14)
    grace = due + timedelta(days=3)

    assert display_status("OPEN", due, grace, due - timedelta(days=1)) == "UPCOMING"
    assert display_status("OPEN", due, grace, due) == "DUE"
    assert display_status("OPEN", due, grace, grace) == "DUE"
    assert display_status("OPEN", due, grace, grace + timedelta(days=1)) == "OVERDUE"
    assert display_status("COMPLETED", due, grace, grace + timedelta(days=10)) == "COMPLETED"


@pytest.mark.parametrize(
    ("goal", "expected"),
    [
        ("LOSE_WEIGHT", (68.6, 69.65)),
        ("GAIN_MUSCLE", (70.17, 70.7)),
        ("MAINTAIN", (69.3, 70.7)),
        ("MEDICAL", (69.3, 70.7)),
    ],
)
def test_du_doan_luu_mot_khoang_thay_vi_mot_con_so(goal, expected):
    assert expected_weight_range(70, goal) == pytest.approx(expected, abs=0.01)


@pytest.mark.parametrize(
    ("has_weight", "meal_days", "expected"),
    [
        (False, 14, "INSUFFICIENT"),
        (True, 0, "INSUFFICIENT"),
        (True, 4, "PARTIAL"),
        (True, 7, "SUFFICIENT"),
    ],
)
def test_danh_gia_chat_luong_du_lieu(has_weight, meal_days, expected):
    assert derive_data_quality(has_weight, meal_days) == expected


@pytest.mark.parametrize(
    ("adherence_pct", "expected"),
    [(0, "LOW"), (49, "LOW"), (50, "MEDIUM"), (79, "MEDIUM"), (80, "HIGH"), (100, "HIGH")],
)
def test_phan_loai_muc_do_tuan_thu(adherence_pct, expected):
    assert derive_adherence(adherence_pct) == expected


def test_chi_danh_gia_ket_qua_khi_du_du_lieu_va_tuan_thu_cao():
    assert derive_outcome(69.5, 69.0, 70.0, "SUFFICIENT", "HIGH") == "WITHIN_EXPECTED_RANGE"
    assert derive_outcome(71.0, 69.0, 70.0, "SUFFICIENT", "HIGH") == "ABOVE_EXPECTED_RANGE"
    assert derive_outcome(68.0, 69.0, 70.0, "SUFFICIENT", "HIGH") == "BELOW_EXPECTED_RANGE"
    assert derive_outcome(71.0, 69.0, 70.0, "PARTIAL", "HIGH") == "NOT_EVALUATED"
    assert derive_outcome(71.0, 69.0, 70.0, "SUFFICIENT", "LOW") == "NOT_EVALUATED"


def test_phat_hien_co_an_toan_khong_phu_thuoc_ai():
    flags = derive_safety_flags(
        baseline_weight_kg=70,
        actual_weight_kg=65,
        energy_level=1,
        hunger_level=5,
        sleep_quality=1,
        goal="MEDICAL",
    )
    assert set(flags) == {"RAPID_WEIGHT_CHANGE", "LOW_ENERGY", "HIGH_HUNGER", "POOR_SLEEP", "MEDICAL_REVIEW"}


@pytest.mark.parametrize(
    ("quality", "adherence", "outcome", "flags", "previous_off_track", "goal", "expected"),
    [
        ("INSUFFICIENT", "HIGH", "NOT_EVALUATED", [], False, "LOSE_WEIGHT", "CONTINUE_AND_TRACK"),
        ("SUFFICIENT", "LOW", "NOT_EVALUATED", [], False, "LOSE_WEIGHT", "IMPROVE_ADHERENCE"),
        ("SUFFICIENT", "MEDIUM", "NOT_EVALUATED", [], False, "LOSE_WEIGHT", "IMPROVE_ADHERENCE"),
        ("SUFFICIENT", "HIGH", "WITHIN_EXPECTED_RANGE", [], False, "LOSE_WEIGHT", "CONTINUE"),
        ("SUFFICIENT", "HIGH", "ABOVE_EXPECTED_RANGE", [], False, "LOSE_WEIGHT", "CONTINUE_AND_MONITOR"),
        ("SUFFICIENT", "HIGH", "ABOVE_EXPECTED_RANGE", [], True, "LOSE_WEIGHT", "ADJUST_PLAN"),
        ("SUFFICIENT", "HIGH", "BELOW_EXPECTED_RANGE", [], True, "LOSE_WEIGHT", "CONTINUE_AND_MONITOR"),
        ("SUFFICIENT", "HIGH", "BELOW_EXPECTED_RANGE", [], True, "GAIN_MUSCLE", "ADJUST_PLAN"),
        ("SUFFICIENT", "HIGH", "ABOVE_EXPECTED_RANGE", [], True, "GAIN_MUSCLE", "CONTINUE_AND_MONITOR"),
        ("SUFFICIENT", "HIGH", "WITHIN_EXPECTED_RANGE", ["LOW_ENERGY"], False, "LOSE_WEIGHT", "NEEDS_REVIEW"),
    ],
)
def test_bang_quyet_dinh_day_du(quality, adherence, outcome, flags, previous_off_track, goal, expected):
    assert derive_recommendation(quality, adherence, outcome, flags, previous_off_track, goal) == expected


def test_chi_de_xuat_kcal_khi_duoc_phep_dieu_chinh():
    assert propose_kcal_target(2000, "LOSE_WEIGHT", "ADJUST_PLAN") == 1800
    assert propose_kcal_target(2000, "GAIN_MUSCLE", "ADJUST_PLAN") == 2200
    assert propose_kcal_target(1250, "LOSE_WEIGHT", "ADJUST_PLAN") == 1200
    assert propose_kcal_target(3900, "GAIN_MUSCLE", "ADJUST_PLAN") == 4000
    assert propose_kcal_target(2000, "MEDICAL", "ADJUST_PLAN") is None
    assert propose_kcal_target(2000, "LOSE_WEIGHT", "CONTINUE") is None


@pytest.mark.parametrize(
    "payload",
    [
        {"actual_weight_kg": 19},
        {"actual_weight_kg": 301},
        {"actual_weight_kg": 70, "actual_waist_cm": 20},
        {"actual_weight_kg": 70, "adherence_pct": 101},
        {"actual_weight_kg": 70, "energy_level": 0},
    ],
)
def test_schema_tu_choi_du_lieu_checkin_phi_logic(payload):
    valid: dict[str, Any] = {
        "actual_weight_kg": 70,
        "actual_activity_level": 3,
        "adherence_pct": 80,
        "energy_level": 3,
        "hunger_level": 3,
        "sleep_quality": 3,
    }
    valid.update(payload)
    with pytest.raises(ValidationError):
        CheckinSubmitIn(**valid)


def _checkin_schema_up() -> bool:
    try:
        with engine.connect() as connection:
            return bool(connection.execute(text("SELECT to_regclass('plan_checkins')")).scalar())
    except Exception:
        return False


@pytest.mark.skipif(not _checkin_schema_up(), reason="Cần PostgreSQL đã áp dụng migration 19")
def test_submit_va_decision_lap_khong_tao_du_lieu_trung():
    from app.models import BodyMetricHistory, NutritionPlan, PlanCheckin, User, UserProfile
    from app.services.plan_checkin import (
        decide_checkin, get_current_checkin, reopen_checkin, simulate_due_checkin,
        start_new_series, submit_checkin,
    )

    db = SessionLocal()
    user = User(email=f"checkin-{uuid.uuid4().hex[:8]}@test.local", password_hash="x", role="USER")
    db.add(user)
    db.flush()
    db.add(UserProfile(
        user_id=user.id, full_name="Người check-in", gender="MALE",
        birth_date=date(2000, 1, 1),
        activity_level=3, goal="MAINTAIN", daily_calorie_target=2000,
    ))
    db.add(BodyMetricHistory(user_id=user.id, height_cm=170, weight_kg=70))
    plan = NutritionPlan(
        user_id=user.id, version=1, start_date=date.today() - timedelta(days=14),
        end_date=date.today(), daily_kcal_target=2000, goal="MAINTAIN",
        content={"days": []}, status="ACTIVE",
    )
    db.add(plan)
    db.flush()
    checkin = start_new_series(db, user, plan, today=date.today())
    db.commit()

    checkin = simulate_due_checkin(db, user, today=date.today())
    db.commit()
    assert checkin.start_date == date.today() - timedelta(days=14)
    assert checkin.period_end == date.today() - timedelta(days=1)
    assert checkin.due_date == date.today()
    assert checkin.grace_until == date.today() + timedelta(days=3)
    with pytest.raises(RuntimeError):
        simulate_due_checkin(db, user, today=date.today())
    db.rollback()

    payload = CheckinSubmitIn(
        actual_weight_kg=70, actual_activity_level=3, adherence_pct=80,
        energy_level=3, hunger_level=3, sleep_quality=3,
    )
    other_user = User(id=uuid.uuid4(), email="other@test.local", password_hash="x", role="USER")
    with pytest.raises(LookupError):
        submit_checkin(db, other_user, checkin.id, payload, today=date.today())
    db.rollback()

    invalid_payload = payload.model_copy(update={"actual_weight_kg": 20})
    with pytest.raises(ValueError, match="quá 20%"):
        submit_checkin(db, user, checkin.id, invalid_payload, today=date.today())
    db.rollback()

    first = submit_checkin(db, user, checkin.id, payload, today=date.today())
    db.commit()
    reopened = reopen_checkin(db, user, checkin.id)
    db.commit()
    assert reopened.status == "OPEN"
    assert reopened.feedback_status == "NOT_REQUESTED"
    first = submit_checkin(db, user, checkin.id, payload, today=date.today())
    db.commit()
    second = submit_checkin(db, user, checkin.id, payload, today=date.today())
    db.commit()
    assert first.id == second.id
    assert db.query(BodyMetricHistory).filter(
        BodyMetricHistory.user_id == user.id,  # type: ignore
        BodyMetricHistory.recorded_at == date.today(),  # type: ignore
    ).count() == 1

    _, next_first = decide_checkin(db, user, checkin.id, "CONTINUE")
    db.commit()
    _, next_second = decide_checkin(db, user, checkin.id, "CONTINUE")
    db.commit()
    assert next_first is not None
    assert next_second is not None
    assert next_first.id == next_second.id
    assert db.query(PlanCheckin).filter(
        PlanCheckin.previous_checkin_id == checkin.id  # type: ignore
    ).count() == 1

    # Demo có thể mô phỏng nhiều kỳ về cùng một khoảng ngày; vẫn phải lấy kỳ mới nhất.
    simulate_due_checkin(db, user, today=date.today())
    db.commit()
    current = get_current_checkin(db, user, today=date.today())
    assert current is not None
    assert current.id == next_first.id

    db.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": str(user.id)})
    db.commit()
    db.close()


@pytest.mark.skipif(not _checkin_schema_up(), reason="Cần PostgreSQL đã áp dụng migration 19")
def test_adjustment_lap_chi_tao_mot_plan_version(monkeypatch):
    from app.models import BodyMetricHistory, NutritionPlan, PlanCheckin, User, UserProfile
    from app.services import plan_generator
    from app.services.plan_checkin import decide_checkin, start_new_series

    monkeypatch.setattr(
        plan_generator,
        "generate_content",
        lambda db, user, target, note=None: ({"days": []}, "test"),
    )
    db = SessionLocal()
    user = User(email=f"adjust-{uuid.uuid4().hex[:8]}@test.local", password_hash="x", role="USER")
    db.add(user)
    db.flush()
    db.add(UserProfile(
        user_id=user.id, full_name="Người điều chỉnh", gender="FEMALE",
        birth_date=date(2000, 1, 1),
        activity_level=3, goal="LOSE_WEIGHT", daily_calorie_target=2000,
    ))
    db.add(BodyMetricHistory(user_id=user.id, height_cm=160, weight_kg=65))
    plan = NutritionPlan(
        user_id=user.id, version=1, start_date=date.today() - timedelta(days=14),
        end_date=date.today(), daily_kcal_target=2000, goal="LOSE_WEIGHT",
        content={"days": []}, status="ACTIVE",
    )
    db.add(plan)
    db.flush()
    checkin = start_new_series(db, user, plan, today=date.today() - timedelta(days=14))
    checkin.status = "COMPLETED"  # type: ignore
    checkin.actual_weight_kg = 65  # type: ignore
    checkin.weight_change_kg = 0  # type: ignore
    checkin.recommendation = "ADJUST_PLAN"  # type: ignore
    checkin.recommendation_reason = "Lệch kỳ vọng hai kỳ liên tiếp."  # type: ignore
    checkin.proposed_kcal_target = 1800  # type: ignore
    db.commit()

    first, next_first = decide_checkin(db, user, checkin.id, "APPLY_ADJUSTMENT")
    db.commit()
    second, next_second = decide_checkin(db, user, checkin.id, "APPLY_ADJUSTMENT")
    db.commit()

    assert str(first.adjusted_plan_id) == str(second.adjusted_plan_id)
    assert next_first is not None
    assert next_second is not None
    assert next_first.id == next_second.id
    assert db.query(NutritionPlan).filter(NutritionPlan.user_id == user.id).count() == 2  # type: ignore
    adjusted = db.query(NutritionPlan).filter(NutritionPlan.id == first.adjusted_plan_id).one()  # type: ignore
    assert str(adjusted.parent_plan_id) == str(plan.id)
    assert adjusted.daily_kcal_target == 1800
    assert db.query(PlanCheckin).filter(
        PlanCheckin.previous_checkin_id == checkin.id  # type: ignore
    ).count() == 1

    db.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": str(user.id)})
    db.commit()
    db.close()

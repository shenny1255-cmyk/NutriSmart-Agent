"""Test logic đánh giá lộ trình 7 ngày (task 12).

Phần logic thuần (decide_result / next_kcal_target) chạy không cần Postgres.
Phần tích hợp (chạy job thật) tự động skip khi DB không bật.
"""
import uuid
from datetime import date, timedelta

import pytest
from sqlalchemy import text

from app.database import SessionLocal, engine
from app.services import plan_evaluator as ev


def _db_up() -> bool:
    try:
        with engine.connect() as c:
            c.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


# ---------- Logic thuần: quyết định ĐẠT / KHÔNG ----------

def test_dat_khi_vua_tuan_thu_calo_vua_dung_huong_can_nang():
    # Mục tiêu giảm cân: nạp sát target + sụt 0.5kg trong 7 ngày → ĐẠT
    assert ev.decide_result(1950, 2000, "LOSE_WEIGHT", -0.5) == "ACHIEVED"


def test_mot_phan_khi_tuan_thu_calo_nhung_can_nang_khong_doi():
    assert ev.decide_result(1950, 2000, "LOSE_WEIGHT", 0.0) == "PARTIAL"


def test_khong_dat_khi_lech_calo_va_can_nang_di_nguoc_muc_tieu():
    # Nạp vượt 30% và còn tăng cân → KHÔNG ĐẠT
    assert ev.decide_result(2600, 2000, "LOSE_WEIGHT", +0.8) == "NOT_ACHIEVED"


def test_khong_dat_khi_khong_co_du_lieu_nhat_ky():
    assert ev.decide_result(None, 2000, "LOSE_WEIGHT", None) == "NOT_ACHIEVED"


def test_thieu_can_nang_nhung_tuan_thu_calo_thi_chi_dat_mot_phan():
    assert ev.decide_result(2000, 2000, "MAINTAIN", None) == "PARTIAL"


def test_muc_tieu_giu_can_dat_khi_can_nang_dao_dong_nho():
    assert ev.decide_result(2050, 2000, "MAINTAIN", -0.3) == "ACHIEVED"


def test_tang_co_can_tang_can_moi_dat():
    assert ev.decide_result(2900, 3000, "GAIN_MUSCLE", +0.4) == "ACHIEVED"
    assert ev.decide_result(2900, 3000, "GAIN_MUSCLE", -0.4) == "PARTIAL"


# ---------- Logic thuần: hiệu chỉnh calo cho phiên bản kế tiếp ----------

def test_dat_thi_giu_nguyen_muc_calo():
    assert ev.next_kcal_target(2000, "ACHIEVED", "LOSE_WEIGHT", -0.5) == 2000


def test_khong_dat_muc_tieu_giam_can_thi_ha_calo():
    new = ev.next_kcal_target(2000, "NOT_ACHIEVED", "LOSE_WEIGHT", +0.5)
    assert 1700 <= new < 2000


def test_khong_dat_muc_tieu_tang_co_thi_nang_calo():
    new = ev.next_kcal_target(3000, "NOT_ACHIEVED", "GAIN_MUSCLE", -0.4)
    assert 3000 < new <= 3400


def test_khong_ha_calo_xuong_duoi_nguong_an_toan():
    assert ev.next_kcal_target(1250, "NOT_ACHIEVED", "LOSE_WEIGHT", +0.2) >= ev.MIN_KCAL


def test_khong_vuot_tran_calo():
    assert ev.next_kcal_target(3950, "NOT_ACHIEVED", "GAIN_MUSCLE", -0.5) <= ev.MAX_KCAL


# ---------- Cửa sổ 7 ngày ----------

def test_plan_chua_du_7_ngay_thi_chua_den_han_danh_gia():
    start = date.today() - timedelta(days=2)
    assert ev.is_due(start, date.today()) is False


def test_plan_du_7_ngay_thi_den_han_danh_gia():
    start = date.today() - timedelta(days=7)
    assert ev.is_due(start, date.today()) is True


# ---------- Tích hợp: chạy job thật trên Postgres ----------

pytestmark_db = pytest.mark.skipif(not _db_up(), reason="Cần Postgres để chạy")


@pytest.fixture
def user_co_plan_qua_han():
    """Tạo user + profile + plan bắt đầu 8 ngày trước + nhật ký ăn, dọn sạch sau test."""
    from app.models import User, UserInfo, HealthProfile, NutritionPlan

    db = SessionLocal()
    u = User(
        email=f"eval-{uuid.uuid4().hex[:8]}@test.local",
        password_hash="x",
        role="USER",
    )
    db.add(u)
    db.flush()
    db.add(UserInfo(user_id=u.id, full_name="Người dùng test"))

    profile = HealthProfile(
        user_id=u.id,
        gender="MALE",
        birth_date=date(2000, 1, 1),
        height_cm=170,
        weight_kg=70,
        activity_level=3,
        goal="LOSE_WEIGHT",
        daily_calorie_target=2000,
    )
    db.add(profile)

    start = date.today() - timedelta(days=8)
    plan = NutritionPlan(
        user_id=u.id,
        version=1,
        start_date=start,
        end_date=start + timedelta(days=7),
        daily_kcal_target=2000,
        goal="LOSE_WEIGHT",
        content={"days": []},
        generated_by="test",
        status="ACTIVE",
    )
    db.add(plan)

    # 7 ngày nhật ký ăn ~2000 kcal/ngày
    for i in range(7):
        db.execute(text("""
            INSERT INTO meal_logs (user_id, meal_type, quantity, calories_kcal, log_date)
            VALUES (:uid, 'LUNCH', 1, 2000, :d)
        """), {"uid": str(u.id), "d": start + timedelta(days=i)})

    db.commit()
    yield db, u, plan

    db.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": str(u.id)})
    db.commit()
    db.close()


@pytestmark_db
def test_job_sinh_evaluation_va_plan_moi(user_co_plan_qua_han, monkeypatch):
    from app.models import NutritionPlan, PlanEvaluation
    from app.services import plan_generator

    # Không gọi LLM thật trong test
    monkeypatch.setattr(plan_generator, "_llm_days", lambda *a, **k: None)
    monkeypatch.setattr(ev, "_llm_feedback", lambda *a, **k: "Nhận xét mẫu")

    db, u, plan = user_co_plan_qua_han
    res = ev.run_plan_job(db, u)

    assert res["evaluated"] is True

    evals = db.query(PlanEvaluation).filter(PlanEvaluation.plan_id == plan.id).all()
    assert len(evals) == 1
    assert evals[0].result in ("ACHIEVED", "PARTIAL", "NOT_ACHIEVED")
    assert float(evals[0].avg_kcal_intake) == pytest.approx(2000, abs=1)

    plans = (
        db.query(NutritionPlan)
        .filter(NutritionPlan.user_id == u.id)
        .order_by(NutritionPlan.version)
        .all()
    )
    assert len(plans) == 2
    assert plans[0].status in ("REVISED", "COMPLETED")   # plan cũ bị hạ
    assert plans[1].version == 2 and plans[1].status == "ACTIVE"


@pytestmark_db
def test_job_khong_danh_gia_lai_cung_mot_ky(user_co_plan_qua_han, monkeypatch):
    from app.models import PlanEvaluation
    from app.services import plan_generator

    monkeypatch.setattr(plan_generator, "_llm_days", lambda *a, **k: None)
    monkeypatch.setattr(ev, "_llm_feedback", lambda *a, **k: "Nhận xét mẫu")

    db, u, plan = user_co_plan_qua_han
    ev.run_plan_job(db, u)
    lan_hai = ev.run_plan_job(db, u)   # plan mới chưa đủ 7 ngày → bỏ qua

    assert lan_hai["evaluated"] is False
    assert db.query(PlanEvaluation).filter(PlanEvaluation.plan_id == plan.id).count() == 1

"""Nhật ký thủ công: ghi bữa ăn, buổi vận động, cập nhật cân nặng (task 13)."""
import uuid
from datetime import date, timedelta

import pytest
from pydantic import ValidationError
from sqlalchemy import text

from app.database import SessionLocal, engine
from app.services.calorie import calories_burned, manual_calories_limit


@pytest.mark.parametrize(
    "payload",
    [
        {"exercise_id": 1, "duration_min": 0},
        {"exercise_id": 1, "duration_min": 601},
        {"exercise_id": 1, "duration_min": 30, "calories_burned": 0},
        {"exercise_id": 1, "duration_min": 30, "calories_burned": 5001},
    ],
)
def test_tu_choi_du_lieu_van_dong_phi_logic(payload):
    from app.schemas import ManualActivityIn

    with pytest.raises(ValidationError):
        ManualActivityIn(**payload)


def _db_up() -> bool:
    try:
        with engine.connect() as c:
            c.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


# ---------- Logic thuần: calo tiêu hao theo MET ----------

def test_calo_tieu_hao_theo_cong_thuc_met():
    # MET 8 (chạy bộ), 70kg, 30 phút → 8 × 3.5 × 70 / 200 × 30 = 294 kcal
    assert calories_burned(met=8.0, weight_kg=70, minutes=30) == pytest.approx(294, abs=0.5)


def test_di_bo_nhe_dot_it_calo_hon_chay_bo():
    di_bo = calories_burned(met=3.5, weight_kg=70, minutes=30)
    chay_bo = calories_burned(met=8.0, weight_kg=70, minutes=30)
    assert di_bo < chay_bo


def test_nguoi_nang_hon_dot_nhieu_calo_hon():
    assert calories_burned(met=5, weight_kg=90, minutes=40) > calories_burned(met=5, weight_kg=60, minutes=40)


def test_thieu_du_lieu_thi_tra_ve_0():
    assert calories_burned(met=None, weight_kg=70, minutes=30) == 0
    assert calories_burned(met=8.0, weight_kg=None, minutes=30) == 0
    assert calories_burned(met=8.0, weight_kg=70, minutes=0) == 0


def test_gioi_han_kcal_nhap_tay_dua_tren_met_can_nang_va_thoi_gian():
    expected, maximum = manual_calories_limit(met=3.5, weight_kg=70, minutes=1)
    assert expected == pytest.approx(4.29, abs=0.1)
    assert maximum < 30
    assert 500 > maximum


def test_thieu_can_nang_van_chan_kcal_vuot_nguong_theo_thoi_gian():
    expected, maximum = manual_calories_limit(met=3.5, weight_kg=None, minutes=1)
    assert expected == 0
    assert maximum == 30


# ---------- Tích hợp ----------

pytestmark_db = pytest.mark.skipif(not _db_up(), reason="Cần Postgres để chạy")


@pytest.fixture
def nguoi_dung():
    from app.models import User, UserInfo

    db = SessionLocal()
    u = User(email=f"diary-{uuid.uuid4().hex[:8]}@test.local", password_hash="x", role="USER")
    db.add(u)
    db.flush()
    db.add(UserInfo(user_id=u.id, full_name="Người ghi nhật ký", gender="MALE", birth_date=date(2000, 1, 1),
                    height_cm=170, weight_kg=70, activity_level=3,
                    goal="LOSE_WEIGHT", daily_calorie_target=2000))
    db.commit()

    yield db, u

    db.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": str(u.id)})
    db.commit()
    db.close()


@pytestmark_db
def test_ghi_bua_an_thu_cong_roi_liet_ke_va_xoa(nguoi_dung):
    from app.routers.tracking import them_bua_an, danh_sach_bua_an, xoa_bua_an
    from app.schemas import ManualMealIn

    db, u = nguoi_dung
    ket_qua = them_bua_an(db, u, ManualMealIn(
        food_name="Phở bò", calories_kcal=430, meal_type="BREAKFAST", quantity=2,
    ))
    # 430 kcal × 2 phần
    assert ket_qua.calories_kcal == pytest.approx(860, abs=0.5)

    hom_nay = danh_sach_bua_an(db, u, date.today())
    assert [m.food_name for m in hom_nay] == ["Phở bò"]

    xoa_bua_an(db, u, ket_qua.id)
    assert danh_sach_bua_an(db, u, date.today()) == []


@pytestmark_db
def test_khong_tao_trung_mon_da_co_trong_danh_muc(nguoi_dung):
    from app.models import Food
    from app.routers.tracking import them_bua_an
    from app.schemas import ManualMealIn

    db, u = nguoi_dung
    truoc = db.query(Food).filter(Food.name == "Phở bò").count()
    them_bua_an(db, u, ManualMealIn(food_name="Phở bò", calories_kcal=430, meal_type="LUNCH"))
    assert db.query(Food).filter(Food.name == "Phở bò").count() == truoc


@pytestmark_db
def test_ghi_van_dong_tu_dong_tinh_calo_theo_met(nguoi_dung):
    from app.models import Exercise
    from app.routers.tracking import them_van_dong, danh_sach_van_dong
    from app.schemas import ManualActivityIn

    db, u = nguoi_dung
    chay_bo = db.query(Exercise).filter(Exercise.name == "Chạy bộ").first()
    assert chay_bo, "Seed thiếu bài tập 'Chạy bộ'"

    ket_qua = them_van_dong(db, u, ManualActivityIn(exercise_id=chay_bo.id, duration_min=30))
    # MET 8 × 70kg × 30 phút
    assert ket_qua.calories_burned == pytest.approx(294, abs=1)
    assert [a.exercise_name for a in danh_sach_van_dong(db, u, date.today())] == ["Chạy bộ"]


@pytestmark_db
def test_nguoi_dung_tu_nhap_calo_thi_khong_tinh_lai(nguoi_dung):
    from app.models import Exercise
    from app.routers.tracking import them_van_dong
    from app.schemas import ManualActivityIn

    db, u = nguoi_dung
    ex = db.query(Exercise).first()
    ket_qua = them_van_dong(db, u, ManualActivityIn(
        exercise_id=ex.id, duration_min=30, calories_burned=200,
    ))
    assert ket_qua.calories_burned == pytest.approx(200, abs=0.5)


@pytestmark_db
def test_chan_kcal_thiet_bi_phi_logic_so_voi_thoi_gian(nguoi_dung):
    from fastapi import HTTPException
    from app.models import Exercise
    from app.routers.tracking import them_van_dong
    from app.schemas import ManualActivityIn

    db, u = nguoi_dung
    ex = db.query(Exercise).first()
    with pytest.raises(HTTPException) as exc:
        them_van_dong(db, u, ManualActivityIn(
            exercise_id=ex.id, duration_min=1, calories_burned=500,
        ))
    assert exc.value.status_code == 422
    assert "quá cao" in str(exc.value.detail)


@pytestmark_db
def test_cap_nhat_can_nang_ghi_lich_su_va_tinh_lai_bmi(nguoi_dung):
    from app.routers.tracking import cap_nhat_can_nang, lich_su_can_nang
    from app.schemas import WeightIn

    db, u = nguoi_dung
    ket_qua = cap_nhat_can_nang(db, u, WeightIn(weight_kg=68))

    assert float(ket_qua.weight_kg) == pytest.approx(68, abs=0.01)
    # BMI = 68 / 1.7² ≈ 23.53 — cột generated của Postgres tự tính
    assert float(ket_qua.bmi) == pytest.approx(23.53, abs=0.05) # type: ignore
    assert float(u.info.weight_kg) == pytest.approx(68, abs=0.01)

    lich_su = lich_su_can_nang(db, u, days=30)
    assert [float(r.weight_kg) for r in lich_su] == [pytest.approx(68, abs=0.01)]


@pytestmark_db
def test_ghi_de_khi_can_nang_cap_nhat_hai_lan_trong_ngay(nguoi_dung):
    from app.routers.tracking import cap_nhat_can_nang, lich_su_can_nang
    from app.schemas import WeightIn

    db, u = nguoi_dung
    cap_nhat_can_nang(db, u, WeightIn(weight_kg=68))
    cap_nhat_can_nang(db, u, WeightIn(weight_kg=67.5))

    lich_su = lich_su_can_nang(db, u, days=30)
    assert len(lich_su) == 1
    assert float(lich_su[0].weight_kg) == pytest.approx(67.5, abs=0.01)


@pytestmark_db
def test_lich_su_can_nang_sap_xep_tang_dan_theo_ngay(nguoi_dung):
    from app.routers.tracking import cap_nhat_can_nang, lich_su_can_nang
    from app.schemas import WeightIn

    db, u = nguoi_dung
    cap_nhat_can_nang(db, u, WeightIn(weight_kg=70, recorded_at=date.today() - timedelta(days=5)))
    cap_nhat_can_nang(db, u, WeightIn(weight_kg=69, recorded_at=date.today() - timedelta(days=2)))
    cap_nhat_can_nang(db, u, WeightIn(weight_kg=68))

    ngay = [r.recorded_at for r in lich_su_can_nang(db, u, days=30)]
    assert ngay == sorted(ngay)

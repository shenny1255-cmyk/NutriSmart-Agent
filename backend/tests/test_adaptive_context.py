"""UAT ISS-01 và ISS-03: dữ liệu Nhật ký 7 ngày vào Lộ trình, ràng buộc cứng cho Trợ lý AI."""
import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from app.database import SessionLocal, engine
from app.services.nutrition_context import render_system_prompt, tracking_summary
from app.services.plan_generator import build_prompt

PROFILE = {"gender": "FEMALE", "age": 30, "height_cm": 158, "weight_kg": 62, "bmi": 24.8,
           "goal": "LOSE_WEIGHT", "conditions": [], "allergens": []}


def test_prompt_lo_trinh_dua_vao_nhat_ky_thuc_te():
    tracking = {"days": 7, "logged_days": 5, "avg_intake": 2150.0, "avg_burned": 180.0}
    prompt = build_prompt(PROFILE, 1700, tracking=tracking)
    assert "Trong 7 ngày qua, người dùng thực tế nạp trung bình 2150 kcal/ngày và tiêu hao 180 kcal/ngày" in prompt
    assert "thâm hụt/thặng dư thực tế" in prompt
    assert "+450 kcal/ngày" in prompt            # nạp vượt mục tiêu 1700
    assert "5/7 ngày" in prompt
    assert "xấp xỉ 1700 kcal" in prompt          # không đổi mục tiêu calo


def test_it_du_lieu_nhat_ky_thi_ghi_ro_chi_tham_khao():
    prompt = build_prompt(PROFILE, 1700, tracking={"days": 7, "logged_days": 1, "avg_intake": 900.0,
                                                   "avg_burned": 0.0})
    assert "chỉ dùng để tham khảo" in prompt


def test_chua_co_nhat_ky_thi_khong_them_khoi_du_lieu_thuc_te():
    assert "thực tế nạp" not in build_prompt(PROFILE, 1700)


def test_tro_ly_bi_rang_buoc_dua_mon_cu_the_va_cam_cau_sao_rong():
    prompt = render_system_prompt({"full_name": "An", "profile": {**PROFILE, "daily_calorie_target": 1700},
                                   "active_plan": None, "tracking": None})
    assert "định lượng ước tính" in prompt and "gam" in prompt and "chén" in prompt
    assert "Cấm tuyệt đối" in prompt and "hãy sống lành mạnh" in prompt
    assert "dị ứng" in prompt


def test_chua_co_ho_so_van_khong_tra_loi_chung_chung():
    prompt = render_system_prompt({"full_name": "An", "profile": None, "active_plan": None, "tracking": None})
    assert "trả lời chung chung" not in prompt
    assert "2000 kcal/ngày" in prompt and "hồ sơ" in prompt


def _db_up() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


@pytest.fixture
def nguoi_dung():
    from app.models import User
    db = SessionLocal()
    user = User(email=f"adaptive-{uuid.uuid4().hex[:8]}@test.local", password_hash="x", role="USER")
    db.add(user)
    db.commit()
    yield db, user
    db.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": str(user.id)})
    db.commit()
    db.close()


@pytest.mark.skipif(not _db_up(), reason="Cần Postgres để chạy")
def test_trung_binh_tinh_tren_ngay_co_ghi_nhat_ky_trong_7_ngay(nguoi_dung):
    from app.models import ActivityLog, MealLog
    db, user = nguoi_dung
    today = date.today()
    noon = lambda d: datetime(d.year, d.month, d.day, 5, 0, tzinfo=timezone.utc)  # 12h giờ Việt Nam
    db.add_all([
        MealLog(user_id=user.id, meal_type="LUNCH", calories_kcal=1200, log_date=today),
        MealLog(user_id=user.id, meal_type="DINNER", calories_kcal=800, log_date=today),
        MealLog(user_id=user.id, meal_type="LUNCH", calories_kcal=1600, log_date=today - timedelta(days=3)),
        MealLog(user_id=user.id, meal_type="LUNCH", calories_kcal=5000, log_date=today - timedelta(days=7)),
        ActivityLog(user_id=user.id, calories_burned=300, started_at=noon(today - timedelta(days=1))),
        ActivityLog(user_id=user.id, calories_burned=999, started_at=noon(today - timedelta(days=9))),
    ])
    db.commit()

    summary = tracking_summary(db, user.id, days=7)
    assert summary["logged_days"] == 2
    assert summary["avg_intake"] == pytest.approx(1800.0)      # (2000 + 1600) / 2 ngày có ghi bữa ăn
    assert summary["avg_burned"] == pytest.approx(100.0)       # 300 / 3 ngày có ghi nhật ký


@pytest.mark.skipif(not _db_up(), reason="Cần Postgres để chạy")
def test_khong_co_bua_an_nao_thi_khong_co_du_lieu_theo_doi(nguoi_dung):
    db, user = nguoi_dung
    assert tracking_summary(db, user.id, days=7) is None


# ---------- Phản hồi người dùng: món dân dã, không lặp thực đơn cũ ----------

def test_prompt_uu_tien_mon_gia_dinh_viet_de_nau():
    prompt = build_prompt(PROFILE, 1700)
    assert "ẩm thực gia đình Việt Nam dân dã" in prompt
    assert "sinh viên và người bận rộn" in prompt


def test_co_thuc_don_cu_thi_yeu_cau_lam_moi_mon_chinh():
    prompt = build_prompt(PROFILE, 1700, previous_meals=["Phở bò", "Cơm gà luộc"])
    assert "Hãy làm mới thực đơn" in prompt and "Phở bò" in prompt and "Cơm gà luộc" in prompt
    assert "Hãy làm mới thực đơn" not in build_prompt(PROFILE, 1700)


def test_lay_ten_mon_cu_khong_trung_va_co_gioi_han():
    from app.services.plan_generator import MAX_PREVIOUS_MEALS, previous_meal_names
    content = {"days": [{"meals": [{"name": "Phở bò"}, {"name": "Cơm gà"}, {"name": " phở bò "}]}] * 2}
    assert previous_meal_names(content) == ["Phở bò", "Cơm gà"]
    many = {"days": [{"meals": [{"name": f"Món {i}"} for i in range(40)]}]}
    assert len(previous_meal_names(many)) == MAX_PREVIOUS_MEALS
    assert previous_meal_names(None) == [] and previous_meal_names({"days": "sai"}) == []


def test_sinh_lo_trinh_khong_con_co_dinh_temperature_0(monkeypatch):
    from app.services import plan_generator
    seen = {}

    def fake_chat(messages, **kwargs):
        seen.update(kwargs)
        raise RuntimeError("không gọi AI thật")
    monkeypatch.setattr(plan_generator.llm, "chat", fake_chat)
    assert plan_generator._llm_days("prompt") is None
    assert seen["temperature"] == plan_generator.PLAN_TEMPERATURE
    assert 0.5 <= plan_generator.PLAN_TEMPERATURE <= 0.6

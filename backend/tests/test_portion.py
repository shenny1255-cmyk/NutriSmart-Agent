"""GĐ3: AI ước lượng gram, kcal tra bảng, sửa khẩu phần được ghi lại để học từ ca sửa."""
import json
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

import app.routers.auth as auth_module
import app.routers.vision as vision_module
from app.database import SessionLocal, engine
from app.main import app
from app.services import food_composition, gemini_vision, portion

RAW = [
    {"name": "Cơm trắng", "grams": 200},
    {"name": "Thịt bò", "grams": 100},
    {"name": "Sốt đặc biệt", "grams": 20, "kcal_per_100g": 200, "protein_per_100g": 2,
     "carb_per_100g": 20, "fat_per_100g": 12},
]


def test_moi_anh_xa_deu_tro_toi_dong_co_that_trong_bang():
    names = {r["name_vi"] for r in food_composition.load_csv()}
    data = json.loads(portion.MAP_PATH.read_text(encoding="utf-8"))
    assert all(item["fct_name"] in names for item in data["items"])


def test_kcal_tra_tu_bang_va_com_chin_khong_tinh_nhu_gao_song():
    com, bo, sot = portion.build_components(RAW)
    assert (com["source"], com["fct_code"]) == ("FCT", "1004")
    assert com["per_100g"]["energy_kcal"] == pytest.approx(344 * 0.356, abs=0.01)
    assert (bo["source"], bo["per_100g"]["energy_kcal"]) == ("FCT", 118.0)
    assert (sot["source"], sot["fct_code"]) == ("AI_ESTIMATE", None)
    assert portion.totals([com, bo, sot])["energy_kcal"] == pytest.approx(402.9, abs=0.1)


def test_khong_ghep_bua_vao_dong_co_ten_gan_giong():
    assert portion.match_component("Thịt bò khô kiểu lạ") is None
    assert portion.match_component("Cá") is None


@pytest.mark.parametrize("bad", [
    [{"name": "Món lạ", "grams": 100}],                                 # không có số ước tính
    [{"name": "Cơm trắng", "grams": 0}],
    [{"name": "Cơm trắng", "grams": 9000}],
    [{"name": "Món lạ", "grams": 50, "kcal_per_100g": 5000, "protein_per_100g": 1,
      "carb_per_100g": 1, "fat_per_100g": 1}],
    [],
    "không phải danh sách",
])
def test_du_lieu_ai_khong_hop_le_thi_khong_tinh_thieu_calo(bad):
    assert portion.build_components(bad) == []


def test_enrich_giu_tong_ai_de_so_sanh_truoc_sau():
    out = portion.enrich({"calories_kcal": 999.0, "protein_g": 1.0, "carb_g": 1.0, "fat_g": 1.0, "components": RAW})
    assert out["ai_total_kcal"] == 999.0
    assert out["calories_kcal"] == pytest.approx(402.9, abs=0.1)


def test_khong_co_thanh_phan_thi_giu_ket_qua_cu():
    out = portion.enrich({"calories_kcal": 450.0, "protein_g": 20.0, "carb_g": 60.0, "fat_g": 10.0})
    assert out["components"] == [] and out["calories_kcal"] == 450.0


def test_normalize_giu_thanh_phan_tu_gemini():
    out = gemini_vision.normalize_food_analysis({
        "is_food_image": True, "food_probability": 0.9, "food_name": "Cơm bò", "calories_kcal": 500,
        "protein_g": 20, "carb_g": 60, "fat_g": 10, "confidence": 0.8, "components": RAW,
    })
    assert out["components"] == RAW


def test_tinh_lai_khong_tin_so_tu_client_va_nhan_biet_ca_sua():
    predicted = portion.build_components(RAW)
    same = [{"name": c["name"], "grams": c["grams"], "fct_code": c["fct_code"]} for c in predicted]
    assert portion.was_corrected(predicted, portion.recalculate(same, predicted)) is False

    edited = [{**same[0], "grams": 150}, same[1], {"name": "Trứng gà", "grams": 50, "fct_code": "9001"}]
    final = portion.recalculate(edited, predicted)
    assert portion.was_corrected(predicted, final) is True
    assert final[2]["per_100g"]["energy_kcal"] == 166.0
    with pytest.raises(ValueError):
        portion.recalculate([{"name": "Tự đặt", "grams": 10, "fct_code": None}], predicted)


def _db_up() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1 FROM vision_feedback LIMIT 1"))
        return True
    except Exception:
        return False


db_only = pytest.mark.skipif(not _db_up(), reason="Postgres tắt hoặc chưa chạy migration 31")
client = TestClient(app)


def _user(monkeypatch, user_test):
    monkeypatch.setattr(auth_module, "send_verification_email", lambda to, link: None)
    email = f"portion_{uuid.uuid4().hex[:10]}@example.com"
    r = client.post("/api/v1/auth/register", json={
        "email": email, "password": "password123", "full_name": "Khẩu Phần",
        "consents": {"terms": True, "health_data": True, "cloud_ai": True},
        "profile": {"gender": "MALE", "birth_date": "1995-01-01", "height_cm": 170, "weight_kg": 65,
                    "activity_level": 3, "goal": "MAINTAIN", "condition_ids": [], "allergen_ids": []},
    })
    assert r.status_code == 201, r.text
    user_test.append(email)
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _scan(monkeypatch, headers):
    monkeypatch.setattr(vision_module, "analyze_food_image", lambda b, mime_type="image/jpeg": {
        "is_food_image": True, "food_probability": 0.95, "rejection_reason": None, "food_name": "Cơm bò",
        "calories_kcal": 700.0, "protein_g": 30.0, "carb_g": 80.0, "fat_g": 20.0, "description": "",
        "confidence": 0.9, "components": RAW[:2],
    })
    r = client.post("/api/v1/vision/analyze-meal", headers=headers, files={"file": ("a.jpg", b"\xff\xd8x", "image/jpeg")})
    assert r.status_code == 200, r.text
    return r.json()


@db_only
def test_luong_quet_sua_gram_luu_va_ghi_feedback(monkeypatch, user_test):
    h = _user(monkeypatch, user_test)
    scan = _scan(monkeypatch, h)
    assert scan["ai_total_kcal"] == 700.0 and scan["calories_kcal"] == pytest.approx(362.9, abs=0.05)

    items = [{"name": c["name"], "grams": c["grams"], "fct_code": c["fct_code"]} for c in scan["components"]]
    items[0]["grams"] = 100
    r = client.post("/api/v1/vision/log-meal", headers=h, json={
        "food_name": "Cơm bò", "calories_kcal": 1, "quantity": 5, "meal_type": "LUNCH",
        "scan_id": scan["scan_id"], "components": items,
    })
    assert r.status_code == 200, r.text
    assert r.json()["added_calories"] == pytest.approx(240.5, abs=0.1)     # server tự tính, bỏ qua số client

    with SessionLocal() as db:
        row = db.execute(text("SELECT status, ai_total_kcal, predicted_kcal, final_kcal, meal_log_id "
                              "FROM vision_feedback WHERE id = :i"), {"i": scan["scan_id"]}).one()
    assert row.status == "CORRECTED" and float(row.ai_total_kcal) == 700.0
    assert float(row.predicted_kcal) == pytest.approx(362.9, abs=0.05)
    assert float(row.final_kcal) == pytest.approx(240.5, abs=0.1) and row.meal_log_id

    again = client.post("/api/v1/vision/log-meal", headers=h, json={
        "food_name": "Cơm bò", "calories_kcal": 1, "scan_id": scan["scan_id"], "components": items})
    assert again.status_code == 409


@db_only
def test_khong_dung_duoc_lan_quet_cua_nguoi_khac(monkeypatch, user_test):
    scan = _scan(monkeypatch, _user(monkeypatch, user_test))
    other = _user(monkeypatch, user_test)
    r = client.post("/api/v1/vision/log-meal", headers=other, json={
        "food_name": "Cơm bò", "calories_kcal": 1, "scan_id": scan["scan_id"],
        "components": [{"name": "Cơm trắng", "grams": 100, "fct_code": "1004"}],
    })
    assert r.status_code == 404

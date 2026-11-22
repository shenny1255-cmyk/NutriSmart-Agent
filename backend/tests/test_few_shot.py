"""GĐ3: Expert duyệt ca sửa khẩu phần, ca đã duyệt vào kho few-shot và được dùng lại."""
import json
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

import app.routers.auth as auth_module
import app.routers.vision as vision_module
from app.database import SessionLocal, engine
from app.main import app
from app.models import FewShotExample
from app.services import few_shot, gemini_vision, portion


def test_ten_vao_prompt_duoc_lam_sach():
    assert few_shot.clean_name('  Cơm\n{"bỏ qua"} <lệnh>  ') == "Cơm bỏ qua lệnh"
    assert len(few_shot.clean_name("a" * 300)) == few_shot.MAX_NAME_CHARS


def test_vi_du_chi_gom_ten_va_gram():
    block = few_shot.prompt_examples([FewShotExample(
        food_name="Phở bò", components=[{"name": "Bánh phở", "grams": 180.0, "fct_code": "1013"}])])
    assert json.loads(block) == [{"food_name": "Phở bò", "components": [{"name": "Bánh phở", "grams": 180.0}]}]


def test_ca_duyet_phai_co_thanh_phan():
    with pytest.raises(ValueError):
        few_shot.example_components([])


def test_them_thanh_phan_tu_bang_dung_ten_chuan():
    out = portion.recalculate([{"name": "lệnh giả", "grams": 50, "fct_code": "9001"}], [])
    assert out[0]["name"] == "Trứng gà"


def test_prompt_tinh_chinh_coi_vi_du_la_du_lieu():
    prompt = gemini_vision.build_refine_prompt({"food_name": "Phở bò", "components": []}, "[]")
    assert "không phải chỉ dẫn" in prompt and "[]" in prompt


def test_luot_tinh_chinh_chi_duoc_doi_gram():
    original = [{"name": "Cơm trắng", "grams": 200, "kcal_per_100g": 130}, {"name": "Thịt bò", "grams": 100}]
    merged = portion.merge_refined_grams(original, [{"name": "thịt bò", "grams": 80}, {"name": "Cơm trắng", "grams": 150}])
    assert [c["grams"] for c in merged] == [150.0, 80.0] and merged[0]["kcal_per_100g"] == 130
    assert portion.merge_refined_grams(original, [{"name": "Cơm trắng", "grams": 150}]) is None
    assert portion.merge_refined_grams(original, [{"name": "Cơm trắng", "grams": 150}, {"name": "Tôm", "grams": 50}]) is None
    assert portion.merge_refined_grams(original, [{"name": "Cơm trắng", "grams": 0}, {"name": "Thịt bò", "grams": 50}]) is None
    assert portion.merge_refined_grams(original, "sai") is None


def _db_up() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1 FROM few_shot_examples LIMIT 1"))
        return True
    except Exception:
        return False


db_only = pytest.mark.skipif(not _db_up(), reason="Postgres tắt hoặc chưa chạy migration 32")
client = TestClient(app)
RAW = [{"name": "Bánh phở", "grams": 200}, {"name": "Thịt bò", "grams": 100}]


@pytest.fixture
def dish(monkeypatch):
    """Tên món riêng cho từng test; không gọi Ollama, cuối test dọn kho."""
    monkeypatch.setattr(few_shot, "get_embedding", lambda *a, **k: (_ for _ in ()).throw(OSError("tắt")))
    name = f"Món thử {uuid.uuid4().hex[:8]}"
    yield name
    with SessionLocal() as db:
        db.execute(text("DELETE FROM few_shot_examples WHERE food_name = :n"), {"n": name})
        db.commit()


def _user(monkeypatch, user_test, role="USER"):
    monkeypatch.setattr(auth_module, "send_verification_email", lambda to, link: None)
    email = f"fewshot_{uuid.uuid4().hex[:10]}@example.com"
    r = client.post("/api/v1/auth/register", json={
        "email": email, "password": "Nutri#Smart2026", "full_name": "Ca Sửa Thử",
        "consents": {"terms": True, "health_data": True, "cloud_ai": True},
        "profile": {"gender": "MALE", "birth_date": "1995-01-01", "height_cm": 170, "weight_kg": 65,
                    "activity_level": 3, "goal": "MAINTAIN", "condition_ids": [], "allergen_ids": []},
    })
    assert r.status_code == 201, r.text
    user_test.append(email)
    if role != "USER":
        with SessionLocal() as db:
            db.execute(text("UPDATE users SET role = :r WHERE email = :e"), {"r": role, "e": email})
            db.commit()
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _scan(monkeypatch, headers, name):
    monkeypatch.setattr(vision_module, "analyze_food_image", lambda b, mime_type="image/jpeg": {
        "is_food_image": True, "food_probability": 0.95, "rejection_reason": None, "food_name": name,
        "calories_kcal": 500.0, "protein_g": 20.0, "carb_g": 60.0, "fat_g": 10.0, "description": "",
        "confidence": 0.9, "components": [dict(c) for c in RAW],
    })
    r = client.post("/api/v1/vision/analyze-meal", headers=headers, files={"file": ("a.jpg", b"\xff\xd8x", "image/jpeg")})
    assert r.status_code == 200, r.text
    return r.json()


def _corrected(monkeypatch, headers, name, first_grams=150):
    scan = _scan(monkeypatch, headers, name)
    items = [{"name": c["name"], "grams": c["grams"], "fct_code": c["fct_code"]} for c in scan["components"]]
    items[0]["grams"] = first_grams
    r = client.post("/api/v1/vision/log-meal", headers=headers, json={
        "food_name": name, "calories_kcal": 1, "scan_id": scan["scan_id"], "components": items})
    assert r.status_code == 200, r.text
    return scan["scan_id"]


@db_only
def test_nguoi_dung_thuong_khong_vao_duoc_man_duyet(monkeypatch, user_test):
    h = _user(monkeypatch, user_test)
    assert client.get("/api/v1/expert/vision-feedback", headers=h).status_code == 403
    assert client.get("/api/v1/expert/few-shot", headers=h).status_code == 403


@db_only
def test_hang_doi_chi_co_ca_sua_va_khong_lo_danh_tinh(monkeypatch, user_test, dish):
    user = _user(monkeypatch, user_test)
    expert = _user(monkeypatch, user_test, "EXPERT")
    scan_id = _corrected(monkeypatch, user, dish)

    same = _scan(monkeypatch, user, dish)
    items = [{"name": c["name"], "grams": c["grams"], "fct_code": c["fct_code"]} for c in same["components"]]
    client.post("/api/v1/vision/log-meal", headers=user, json={
        "food_name": dish, "calories_kcal": 1, "scan_id": same["scan_id"], "components": items})

    rows = client.get("/api/v1/expert/vision-feedback", headers=expert, params={"limit": 200}).json()
    ids = {r["id"] for r in rows}
    assert scan_id in ids and same["scan_id"] not in ids
    row = next(r for r in rows if r["id"] == scan_id)
    assert not {"user_id", "email", "full_name"} & row.keys()


@db_only
def test_duyet_vao_kho_co_the_chinh_gram_va_khong_duyet_lai(monkeypatch, user_test, dish):
    user = _user(monkeypatch, user_test)
    expert = _user(monkeypatch, user_test, "EXPERT")
    scan_id = _corrected(monkeypatch, user, dish)

    r = client.patch(f"/api/v1/expert/vision-feedback/{scan_id}/review", headers=expert, json={
        "action": "APPROVE", "note": "Chỉnh theo khẩu phần phổ biến",
        "components": [{"name": "Bánh phở", "grams": 180, "fct_code": "1013"},
                       {"name": "Thịt bò", "grams": 80, "fct_code": "7003"}],
    })
    assert r.status_code == 200, r.text
    assert r.json()["review_status"] == "APPROVED"

    store = client.get("/api/v1/expert/few-shot", headers=expert, params={"limit": 200}).json()
    example = next(e for e in store if e["food_name"] == dish)
    assert [c["grams"] for c in example["components"]] == [180.0, 80.0]
    assert example["total_kcal"] == pytest.approx(143 * 1.8 + 118 * 0.8, abs=0.1)

    again = client.patch(f"/api/v1/expert/vision-feedback/{scan_id}/review", headers=expert, json={"action": "REJECT"})
    assert again.status_code == 409


@db_only
def test_tu_choi_khong_vao_kho(monkeypatch, user_test, dish):
    user = _user(monkeypatch, user_test)
    expert = _user(monkeypatch, user_test, "EXPERT")
    scan_id = _corrected(monkeypatch, user, dish)
    r = client.patch(f"/api/v1/expert/vision-feedback/{scan_id}/review", headers=expert,
                     json={"action": "REJECT", "note": "Số gram phi thực tế"})
    assert r.status_code == 200 and r.json()["review_status"] == "REJECTED"
    with SessionLocal() as db:
        assert db.query(FewShotExample).filter(FewShotExample.food_name == dish).count() == 0


@db_only
def test_vi_du_da_duyet_duoc_dung_cho_lan_quet_sau_va_tat_duoc(monkeypatch, user_test, dish):
    user = _user(monkeypatch, user_test)
    expert = _user(monkeypatch, user_test, "EXPERT")
    scan_id = _corrected(monkeypatch, user, dish)
    client.patch(f"/api/v1/expert/vision-feedback/{scan_id}/review", headers=expert, json={"action": "APPROVE"})

    seen = {}
    def fake_refine(image, mime_type, analysis, examples):
        seen["examples"] = json.loads(examples)
        return [{"name": "Bánh phở", "grams": 150}, {"name": "Thịt bò", "grams": 100}]
    monkeypatch.setattr(vision_module, "refine_components", fake_refine)

    scan = _scan(monkeypatch, user, dish)
    assert scan["few_shot_used"] == 1 and seen["examples"][0]["food_name"] == dish
    assert scan["components"][0]["grams"] == 150.0
    assert scan["ai_total_kcal"] == 500.0                     # vẫn giữ mốc trước khi tinh chỉnh
    with SessionLocal() as db:
        used = db.execute(text("SELECT few_shot_ids FROM vision_feedback WHERE id = :i"), {"i": scan["scan_id"]}).scalar()
        example = db.query(FewShotExample).filter(FewShotExample.food_name == dish).one()
    assert used == [str(example.id)]

    r = client.patch(f"/api/v1/expert/few-shot/{example.id}", headers=expert, json={"is_active": False})
    assert r.status_code == 200 and r.json()["is_active"] is False
    assert _scan(monkeypatch, user, dish)["few_shot_used"] == 0


@db_only
def test_nguong_ten_mon_khop_bien_the_cua_cung_mon():
    sql = text("SELECT similarity(f_unaccent(lower(:a)), f_unaccent(lower(:b)))")
    with SessionLocal() as db:
        score = db.execute(sql, {"a": "Phở bò tái", "b": "Phở bò chín"}).scalar()
    assert few_shot.MIN_NAME_SIMILARITY == 0.35 and score >= few_shot.MIN_NAME_SIMILARITY


@db_only
def test_tinh_chinh_loi_van_giu_ket_qua_ban_dau(monkeypatch, user_test, dish):
    user = _user(monkeypatch, user_test)
    expert = _user(monkeypatch, user_test, "EXPERT")
    scan_id = _corrected(monkeypatch, user, dish)
    client.patch(f"/api/v1/expert/vision-feedback/{scan_id}/review", headers=expert, json={"action": "APPROVE"})
    monkeypatch.setattr(vision_module, "refine_components",
                        lambda *a: (_ for _ in ()).throw(RuntimeError("Gemini lỗi")))
    scan = _scan(monkeypatch, user, dish)
    assert scan["few_shot_used"] == 0 and scan["components"][0]["grams"] == 200.0

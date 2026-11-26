"""Hồi quy cho 8 lỗi phát hiện ở đợt QA nghiệm thu (B1-B8).

Phần cần Postgres tự bỏ qua khi DB chưa chạy.
"""

import uuid
from datetime import date, timedelta
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.database import SessionLocal, engine
from app.main import app
from app.security import create_pin_verified_token
from app.services import accent_restore, guardrails, llm, privacy
from app.services.nutrition_context import render_system_prompt


def _db_up() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


needs_db = pytest.mark.skipif(not _db_up(), reason="Postgres chưa chạy")
client = TestClient(app, raise_server_exceptions=False)


def _user(user_test) -> dict:
    email = f"qafix_{uuid.uuid4().hex[:10]}@example.com"
    r = client.post("/api/v1/auth/register", json={
        "email": email, "password": "Nutri#Smart2026", "full_name": "Kiểm Thử",
        "pin_token": create_pin_verified_token(email),
        "consents": {"terms": True, "health_data": True, "cloud_ai": True},
        "profile": {"gender": "MALE", "birth_date": "1996-01-01", "height_cm": 170, "weight_kg": 70,
                    "activity_level": 3, "goal": "MAINTAIN", "condition_ids": [], "allergen_ids": []},
    })
    assert r.status_code == 201, r.text
    user_test.append(email)
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _xoa_mon(ten: str) -> None:
    """Xóa món test cùng các bữa ăn trỏ tới nó (chạy trước khi fixture user_test xóa tài khoản)."""
    with SessionLocal() as db:
        db.execute(text("DELETE FROM meal_logs WHERE food_id IN (SELECT id FROM foods WHERE name = :n)"), {"n": ten})
        db.execute(text("DELETE FROM foods WHERE name = :n"), {"n": ten})
        db.commit()


# ---------- B1: /vision/log-meal phải chặn số liệu phi lý và không lộ lỗi CSDL ----------

@needs_db
@pytest.mark.parametrize("extra", [
    {"calories_kcal": 99_999_999},
    {"protein_g": -50},
    {"carb_g": -1},
    {"fat_g": -1},
    {"quantity": 1000},
    {"log_date": str(date.today() + timedelta(days=3))},
])
def test_vision_log_meal_chan_gia_tri_phi_ly(user_test, extra):
    headers = _user(user_test)
    body = {"food_name": "Cơm rang QA", "calories_kcal": 300, "meal_type": "SNACK", **extra}
    r = client.post("/api/v1/vision/log-meal", headers=headers, json=body)
    assert r.status_code == 422, r.text


@needs_db
def test_tracking_meals_chan_ngay_tuong_lai(user_test):
    headers = _user(user_test)
    r = client.post("/api/v1/tracking/meals", headers=headers, json={
        "food_name": "Cơm rang QA", "calories_kcal": 300, "meal_type": "SNACK",
        "log_date": str(date.today() + timedelta(days=3)),
    })
    assert r.status_code == 422, r.text


@needs_db
def test_loi_luu_bua_an_khong_lo_cau_sql(user_test, monkeypatch):
    import app.routers.vision as vision_router

    def hong(*_a, **_k):
        raise RuntimeError("INSERT INTO meal_logs (user_id) VALUES ('bí mật')")
    monkeypatch.setattr(vision_router, "sync_meal_log_with_plan", hong)
    headers = _user(user_test)
    r = client.post("/api/v1/vision/log-meal", headers=headers,
                    json={"food_name": "Cơm rang QA", "calories_kcal": 300, "meal_type": "SNACK"})
    assert r.status_code == 500
    assert "INSERT" not in r.text and "bí mật" not in r.text


@needs_db
def test_ten_mon_co_ky_tu_phan_tram_khong_khop_mon_khac(user_test):
    """'%' được phép trong tên món; không được hiểu là ký tự đại diện của LIKE."""
    headers = _user(user_test)
    r = client.post("/api/v1/tracking/meals", headers=headers,
                    json={"food_name": "Sữa chua 100%", "calories_kcal": 120, "meal_type": "SNACK"})
    try:
        assert r.status_code == 200, r.text
        assert r.json()["food_name"] == "Sữa chua 100%"
        r2 = client.post("/api/v1/tracking/meals", headers=headers,
                         json={"food_name": "Sữa%", "calories_kcal": 90, "meal_type": "SNACK"})
        assert r2.status_code == 200, r2.text
        assert r2.json()["food_name"] == "Sữa%"
    finally:
        _xoa_mon("Sữa%")


# ---------- B2: id sai định dạng UUID → 422, không phải 500 ----------

@needs_db
@pytest.mark.parametrize("method,path,body,who", [
    ("patch", "/api/v1/expert/documents/abc/review", {"status": "REJECTED"}, "expert1@nutrismart.vn"),
    ("get", "/api/v1/expert/documents/abc/preview", None, "expert1@nutrismart.vn"),
    ("patch", "/api/v1/expert/documents/abc/category", {"category_id": 1}, "expert1@nutrismart.vn"),
    ("delete", "/api/v1/expert/crawl-sources/abc", None, "expert1@nutrismart.vn"),
    ("delete", "/api/v1/admin/users/abc", None, "demo@nutrismart.vn"),
])
def test_id_sai_dinh_dang_tra_422(method, path, body, who):
    login = client.post("/api/v1/auth/login", json={"email": who, "password": "demo1234"})
    if login.status_code != 200:
        pytest.skip("Chưa seed tài khoản demo")
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    kwargs = {"json": body} if body else {}
    r = getattr(client, method)(path, headers=headers, **kwargs)
    assert r.status_code == 422, r.text


# ---------- B3: khôi phục dấu cho câu hỏi gõ không dấu ----------

KHO = [
    "Người bệnh đái tháo đường nên kiêng đồ ngọt, hạn chế tinh bột hấp thu nhanh.",
    "Người bệnh gout nên kiêng nội tạng, hải sản và bia rượu.",
    "Ăn nhiều rau xanh giúp kiểm soát đường huyết.",
]


def test_khong_dau_nhan_dien_dung():
    assert accent_restore.has_diacritics("tiểu đường") is True
    assert accent_restore.has_diacritics("tieu duong kieng an gi") is False
    assert accent_restore.strip_accents("Đái tháo đường") == "Dai thao duong"


def test_khoi_phuc_dau_tu_kho_tai_lieu():
    index = accent_restore.build_index(KHO)
    assert accent_restore.restore("nguoi benh gout nen kieng gi", index) == "người bệnh gout nên kiêng gì" or \
        accent_restore.restore("nguoi benh gout nen kieng gi", index).startswith("người bệnh gout nên kiêng")
    assert accent_restore.restore("dai thao duong kieng do ngot", index) == "đái tháo đường kiêng đồ ngọt"


def test_tu_khong_co_trong_kho_giu_nguyen():
    index = accent_restore.build_index(KHO)
    assert accent_restore.restore("xyz bmi", index) == "xyz bmi"


# ---------- B4: tên dị ứng ghép phải quy về nhóm dị nguyên ----------

@pytest.mark.parametrize("ten,mon", [
    ("tôm hùm đất", "Gỏi cuốn tôm thịt"),
    ("cá ngừ", "Bún chả"),
    ("sữa bò tươi", "Sữa chua nếp cẩm"),
])
def test_ten_di_ung_ghep_van_canh_bao(ten, mon):
    ws = guardrails.check_food_text(mon, guardrails.GuardProfile(allergens=(ten,)))
    assert any(w["level"] == "DANGER" and w["code"] == "ALLERGEN" for w in ws), ws


def test_ten_di_ung_ghep_khong_bat_nham_nhom():
    """'trứng gà' là dị ứng trứng, không phải dị ứng thịt gà."""
    ws = guardrails.check_food_text("Gà luộc", guardrails.GuardProfile(allergens=("trứng gà",)))
    assert not ws, ws
    ws = guardrails.check_food_text("Sữa đậu nành", guardrails.GuardProfile(allergens=("sữa bò tươi",)))
    assert not ws, ws


# ---------- B5: tuổi trong câu tự do cũng phải làm mờ ----------

def test_an_danh_tuoi_trong_cau_tu_do():
    out, report = privacy.anonymize_messages([{"role": "user", "content": "Năm nay tôi 22 tuổi, nặng 70kg"}])
    assert "22 tuổi" not in out[0]["content"]
    assert "18-24 tuổi" in out[0]["content"]
    assert report["age"] == 1


def test_an_danh_khong_dong_vao_so_khac():
    out, _ = privacy.anonymize_messages([{"role": "user", "content": "Ăn 2 quả trứng, 150 gam cơm"}])
    assert out[0]["content"] == "Ăn 2 quả trứng, 150 gam cơm"


# ---------- B6: audit của stream ghi đúng model thực sự trả lời ----------

def test_audit_stream_ghi_model_du_phong(monkeypatch):
    from app.config import settings

    class Models:
        def generate_content_stream(self, model, contents, config):
            if model == llm._gemini_models()[0]:
                raise RuntimeError("503 quá tải")
            yield SimpleNamespace(text="Xin chào")

    calls = []
    monkeypatch.setattr(settings, "LLM_PROVIDER", "gemini")
    monkeypatch.setattr(llm, "_gemini_client", lambda timeout: SimpleNamespace(models=Models()))
    monkeypatch.setattr(llm, "_audit_external_call", lambda **kw: calls.append(kw))
    user = SimpleNamespace(id=None, profile=SimpleNamespace(ai_local_only=False, full_name=None))
    assert "".join(llm.chat_stream([{"role": "user", "content": "hi"}], user=user)) == "Xin chào"
    ok = [c for c in calls if c["ok"]]
    assert ok and ok[-1]["model"] == llm._gemini_models()[1]


# ---------- B7: lưu cùng một món từ ảnh không nhân bản bảng foods ----------

@needs_db
def test_vision_log_meal_dung_lai_mon_giong_het(user_test):
    headers = _user(user_test)
    ten = f"Cơm bò QA {uuid.uuid4().hex[:6]}"
    body = {"food_name": ten, "calories_kcal": 650, "protein_g": 30, "carb_g": 80, "fat_g": 20, "meal_type": "LUNCH"}
    try:
        for _ in range(3):
            assert client.post("/api/v1/vision/log-meal", headers=headers, json=body).status_code == 200
        with SessionLocal() as db:
            n = db.execute(text("SELECT count(*) FROM foods WHERE name = :n"), {"n": ten}).scalar()
        assert n == 1
    finally:
        with SessionLocal() as db:
            db.execute(text("DELETE FROM meal_logs WHERE item_name_snapshot = :n"), {"n": ten})
            db.execute(text("DELETE FROM foods WHERE name = :n"), {"n": ten})
            db.commit()


# ---------- B8: trợ lý giữ phạm vi dinh dưỡng - sức khỏe ----------

def test_system_prompt_gioi_han_pham_vi():
    prompt = render_system_prompt({})
    assert "ngoài phạm vi" in prompt


@needs_db
@pytest.mark.parametrize("path", ["/api/v1/chat/messages", "/api/v1/chat/stream"])
def test_chat_tu_choi_cau_ngoai_pham_vi_khong_goi_llm(user_test, monkeypatch, path):
    import app.routers.chat as chat_router
    from app.services import topic_guard

    def khong_duoc_goi(*_a, **_k):
        raise AssertionError("Không được gọi LLM cho câu ngoài phạm vi")
    monkeypatch.setattr(chat_router, "_chat", khong_duoc_goi)
    monkeypatch.setattr(chat_router, "_chat_stream", khong_duoc_goi)
    monkeypatch.setattr(chat_router.retrieval, "search_chunks", lambda *a, **k: [])
    headers = _user(user_test)
    r = client.post(path, headers=headers, json={"message": "Cách thay lốp xe máy bị thủng?"})
    assert r.status_code == 200, r.text
    assert topic_guard.REFUSAL[:40] in r.text
    hist = client.get("/api/v1/chat/messages", headers=headers).json()
    assert [m["role"] for m in hist] == ["user", "assistant"]


@needs_db
def test_chat_cau_dinh_duong_van_goi_llm(user_test, monkeypatch):
    import app.routers.chat as chat_router
    monkeypatch.setattr(chat_router, "_chat", lambda messages, user: "Nên ăn rau xanh.")
    monkeypatch.setattr(chat_router.retrieval, "search_chunks", lambda *a, **k: [])
    headers = _user(user_test)
    r = client.post("/api/v1/chat/messages", headers=headers, json={"message": "Tối nay mình nên ăn gì?"})
    assert r.status_code == 200 and r.json()["reply"] == "Nên ăn rau xanh."

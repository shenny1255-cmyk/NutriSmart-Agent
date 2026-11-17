"""Bảng thành phần thực phẩm Việt Nam (Viện Dinh dưỡng 2007) - GĐ1.

- Bộ trích xuất PDF (scripts/import_vn_fct.py): giải mã TCVN3, tách số dính mã nguồn.
- File dữ liệu data/food_composition_vn2007.csv: kiểm tra tính toàn vẹn.
- Dịch vụ tra cứu: quy đổi theo gram (thuần) và tìm kiếm trong Postgres (bỏ qua khi DB tắt).
"""
import importlib.util
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.database import SessionLocal
from app.services import food_composition as fc

BACKEND = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("import_vn_fct", BACKEND / "scripts" / "import_vn_fct.py")
imp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(imp)  # type: ignore[union-attr]


# ---------- Bộ trích xuất ----------

def test_giai_ma_tcvn3():
    assert imp.tcvn3_to_unicode("G¹o nÕp c¸i") == "Gạo nếp cái"
    assert imp.tcvn3_to_unicode("Ng« b¾p t−¬i") == "Ngô bắp tươi"
    assert imp.tcvn3_to_unicode("Bét m×") == "Bột mì"
    # Chữ hoa có dấu nằm ở font riêng nên ra chữ thường → viết hoa lại chữ đầu
    assert imp.tcvn3_to_unicode("ít ®á to") == "Ớt đỏ to"


def test_tach_so_dinh_ma_nguon():
    assert imp.parse_int_token("01") == (0.0, False)      # 0, nguồn 1
    assert imp.parse_int_token("282 1") == (282.0, False)
    assert imp.parse_int_token("-") == (None, False)
    assert imp.parse_int_token("31") == (None, True)      # 3 (nguồn 1) hay 31? → mơ hồ


PAGE = """STT: 1
M· sè: 1001
Th¶i bá (%): 0.0
Nước (Water ) g 14.0 1 Tổng số isoflavon (Total isoflavone) mg -
Năng lượng (Energy ) KCal 344 Daidzein mg -
Protein g 8.6 1 Glycetin mg -
Lipid (Fat) g 1.5 1 Tổng số acid béo no g -
Glucid (Carbohydrate) g 74.5 1 (Total saturated fatty acid)
Celluloza (Fiber) g 0.6 1 Palmitic (C16:0) g -
Đường tổng số (Sugar) g - Stearic (C18:0) g -
Tªn thùc phÈm (Vietnamese): G¹o nÕp c¸i
Tªn tiÕng Anh (English): Glutinous rice, milled
Natri (Sodium) mg 31 Arachidonic (C20:4) g -
Vitamin C (Ascorbic acid) mg 01 Cholesterol mg 02
Purin mg - Serin mg 309 2
1
"""


def test_doc_trang_chi_tiet():
    r = imp.parse_page(PAGE)
    assert r["code"] == "1001" and r["name_vi"] == "Gạo nếp cái"
    assert r["name_en"] == "Glutinous rice, milled"
    assert (r["energy_kcal"], r["protein_g"], r["fat_g"], r["carb_g"]) == (344, 8.6, 1.5, 74.5)
    assert r["cholesterol_mg"] == 0.0          # "02" = 0, nguồn 2 - không phải 2 mg
    assert r["sodium_mg"] is None and r["ambiguous"]
    assert r["book_page"] == 1
    assert r["food_group"] == "Ngũ cốc và sản phẩm chế biến"


def test_doc_trang_kieu_ten_dau_trang():
    page = PAGE.replace("STT: 1\nM· sè: 1001", "Nhéng STT: 359\nSilk worm M· sè: 7081") \
               .replace("Tªn thùc phÈm (Vietnamese): G¹o nÕp c¸i", "Tªn thùc phÈm (Vietnamese):") \
               .replace("Tªn tiÕng Anh (English): Glutinous rice, milled", "Tªn tiÕng Anh (English):")
    r = imp.parse_page(page)
    assert (r["code"], r["name_vi"], r["name_en"]) == ("7081", "Nhộng", "Silk worm")


def test_kiem_tra_atwater():
    assert imp.atwater_check({"energy_kcal": 344, "protein_g": 8.6, "fat_g": 1.5, "carb_g": 74.5}) == ""
    assert "lệch" in imp.atwater_check({"energy_kcal": 273, "protein_g": 0, "fat_g": 0, "carb_g": 0})


# ---------- File dữ liệu ----------

def test_file_du_lieu_toan_ven():
    rows = fc.load_csv()
    assert len(rows) >= 500
    codes = [r["code"] for r in rows]
    assert len(codes) == len(set(codes))
    for r in rows:
        assert r["name_vi"] and r["energy_kcal"] is not None, r["code"]
        assert r["book_page"], r["code"]
        for k in ("protein_g", "fat_g", "carb_g"):
            assert r[k] is None or r[k] >= 0
        assert r["review_status"] in fc.REVIEW_STATUSES
    # Dòng lệch Atwater phải được đánh dấu cho nhóm duyệt, không được lọt im lặng
    for r in rows:
        if imp.atwater_check(r):
            assert r["check_note"], r["code"]


def test_gia_tri_mau_khop_bang_goc():
    by_code = {r["code"]: r for r in fc.load_csv()}
    trung = by_code["9001"]
    assert trung["name_vi"] == "Trứng gà"
    assert (trung["energy_kcal"], trung["protein_g"], trung["fat_g"]) == (166, 14.8, 11.6)


# ---------- Quy đổi theo gram ----------

def test_quy_doi_theo_gram():
    gao = {"energy_kcal": 344.0, "protein_g": 7.9, "fat_g": 1.0, "carb_g": 75.9, "fiber_g": None}
    out = fc.scale(gao, 150)
    assert out["grams"] == 150
    assert out["energy_kcal"] == pytest.approx(516.0)
    assert out["protein_g"] == pytest.approx(11.85)
    assert out["fiber_g"] is None              # thiếu số liệu giữ nguyên là thiếu, không đoán 0


def test_quy_doi_tu_chua_phan_thai_bo():
    # Cân cả vỏ/xương → trừ % thải bỏ trước khi tính
    chuoi = {"energy_kcal": 97.0, "waste_pct": 20.0}
    assert fc.scale(chuoi, 100, as_purchased=True)["energy_kcal"] == pytest.approx(77.6)


# ---------- Postgres + API ----------

def _db_up() -> bool:
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1 FROM food_composition LIMIT 1"))
        db.close()
        return True
    except Exception:
        return False


db_only = pytest.mark.skipif(not _db_up(), reason="Postgres tắt hoặc chưa chạy migration 29")


@db_only
def test_dong_bo_va_tim_khong_dau():
    db = SessionLocal()
    try:
        assert fc.sync_from_csv(db) >= 500
        assert fc.sync_from_csv(db) >= 500       # chạy lại không lỗi (upsert)
        names = [r.name_vi for r in fc.search(db, "gao te may")]
        assert names and names[0] == "Gạo tẻ máy"
    finally:
        db.close()


@db_only
def test_api_tra_cuu():
    from app.main import app
    client = TestClient(app)
    r = client.get("/api/v1/catalog/food-composition", params={"q": "trứng gà"})
    assert r.status_code == 200
    first = r.json()[0]
    assert first["name_vi"] == "Trứng gà" and first["source"].startswith("Viện Dinh dưỡng")

    r = client.get("/api/v1/catalog/food-composition/9001", params={"grams": 50})
    assert r.status_code == 200
    assert r.json()["per_portion"]["energy_kcal"] == pytest.approx(83.0)

    assert client.get("/api/v1/catalog/food-composition/0000").status_code == 404

"""Bảng món → nguyên liệu cho Warning Engine (GĐ1): bắt dị ứng ẩn trong tên món.

Logic thuần, không cần Postgres hay LLM.
"""
from app.services import guardrails as g
from app.services.guardrails import GuardProfile


def _codes(ws):
    return [w["code"] for w in ws]


# ---------- Dữ liệu bảng món ----------

def test_bang_mon_hop_le_va_khong_trung_ten():
    dishes = g.load_dishes()
    assert len(dishes) >= 60
    seen = set()
    for d in dishes:
        assert d.ingredients, d.name
        for n in d.names:
            assert n == g._norm(n)          # đã chuẩn hóa
            assert n not in seen, f"tên/alias trùng: {n}"
            seen.add(n)


def test_nguyen_lieu_khong_dung_tu_de_gay_bao_dong_gia():
    # "ruốc" trần = giáp xác, "bánh đa nem" chứa "bánh đa" (từ khóa mè) → phải viết rõ
    for d in g.load_dishes():
        for ing in d.ingredients:
            assert ing != "ruốc", d.name
            assert "bánh đa nem" not in ing, d.name


# ---------- Dị ứng ẩn ----------

def test_ten_mon_khong_lo_nguyen_lieu_van_canh_bao_di_ung():
    p = GuardProfile(allergens=("Hải sản có vỏ",))
    ws = g.check_food_text("Bánh xèo", p)
    assert _codes(ws) == ["ALLERGEN"]
    assert ws[0]["level"] == "DANGER"
    # Thông điệp nói rõ là suy ra từ công thức phổ biến, kèm nguyên liệu
    assert "thường có" in ws[0]["message"] and "tôm" in ws[0]["message"]


def test_tu_khoa_hien_trong_ten_mon_giu_thong_diep_cu():
    p = GuardProfile(allergens=("Hải sản có vỏ",))
    ws = g.check_food_text("Tôm rang thịt ba chỉ", p)
    assert ws[0]["message"].startswith("Món có “tôm”")


def test_ten_mon_trong_cau_dai_van_nhan_ra():
    p = GuardProfile(allergens=("Cá",))
    assert _codes(g.check_food_text("Bữa trưa: Bún chả Hà Nội, 1 tô", p)) == ["ALLERGEN"]


def test_uu_tien_ten_mon_dai_nhat():
    # "bún bò" là alias của Bún bò Huế (có chả cua, mắm ruốc); "Bún bò Nam Bộ" là món khác, không có
    p = GuardProfile(allergens=("Hải sản có vỏ",))
    assert g.check_food_text("Bún bò Nam Bộ", p) == []
    assert _codes(g.check_food_text("Bún bò Huế", p)) == ["ALLERGEN"]


def test_ca_am_khong_bao_dong_gia():
    assert g.check_food_text("Phở gà", GuardProfile(allergens=("Thịt bò",))) == []
    assert g.check_food_text("Bún chả", GuardProfile(allergens=("Hải sản có vỏ",))) == []
    assert g.check_food_text("Phở bò", GuardProfile(allergens=("Gluten",))) == []


def test_mot_canh_bao_cho_moi_di_nguyen():
    # Có từ khóa hiện ("tôm") lẫn nguyên liệu ẩn của món → vẫn chỉ 1 cảnh báo cho nhóm đó
    p = GuardProfile(allergens=("Hải sản có vỏ",))
    assert len(g.check_food_text("Bánh xèo tôm", p)) == 1


# ---------- Bệnh nền qua cờ lượng ----------

def test_co_luong_bat_benh_nen():
    assert _codes(g.check_food_text("Thịt kho tàu", GuardProfile(conditions=("Tăng huyết áp",)))) == ["CONDITION"]
    assert _codes(g.check_food_text("Bánh bò nướng", GuardProfile(conditions=("Đái tháo đường típ 2",)))) == ["CONDITION"]
    assert _codes(g.check_food_text("Chả giò", GuardProfile(conditions=("Rối loạn lipid máu",)))) == ["CONDITION"]


def test_mon_man_co_nuoc_mam_khong_bi_coi_la_nhieu_duong_hay_muoi():
    assert g.check_food_text("Bún chả", GuardProfile(conditions=("Đái tháo đường típ 2",))) == []
    assert g.check_food_text("Bánh cuốn", GuardProfile(conditions=("Tăng huyết áp",))) == []

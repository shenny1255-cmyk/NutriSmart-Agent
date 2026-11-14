"""Test Warning Engine (guardrails rule-based) - mục 2.5 kế hoạch ĐATN v2.

Toàn bộ là logic thuần, không cần Postgres hay LLM.
"""
from app.services import guardrails as g
from app.services.guardrails import GuardProfile


def _codes(warnings):
    return [w["code"] for w in warnings]


def _levels(warnings):
    return {w["level"] for w in warnings}


# ---------- Ngưỡng calo theo giới tính ----------

def test_nguong_calo_toi_thieu_theo_gioi_tinh():
    assert g.min_kcal_for("FEMALE") == 1200
    assert g.min_kcal_for("MALE") == 1500
    # Không rõ giới tính → dùng mốc thấp hơn để không báo động giả
    assert g.min_kcal_for(None) == 1200
    assert g.min_kcal_for("OTHER") == 1200


def test_ngay_duoi_muc_toi_thieu_la_canh_bao_do():
    nam = GuardProfile(gender="MALE", daily_kcal_target=2000)
    ws = g.check_day_kcal(1400, nam)
    assert _codes(ws) == ["KCAL_LOW"]
    assert ws[0]["level"] == "DANGER"
    # Cùng 1400 kcal với nữ thì không sao
    assert g.check_day_kcal(1400, GuardProfile(gender="FEMALE", daily_kcal_target=1500)) == []


def test_ngay_vuot_120_phan_tram_chi_tieu_la_canh_bao_vang():
    p = GuardProfile(gender="FEMALE", daily_kcal_target=1800)
    ws = g.check_day_kcal(2200, p)       # 122%
    assert _codes(ws) == ["KCAL_HIGH"]
    assert ws[0]["level"] == "WARNING"
    assert g.check_day_kcal(2150, p) == []   # 119% vẫn ổn


# ---------- Dị ứng ----------

def test_di_ung_hai_san_bat_duoc_tu_dong_nghia():
    p = GuardProfile(allergens=("Hải sản có vỏ",))
    for mon in ["Canh cua rau đay", "Ghẹ hấp", "Bún riêu", "Gỏi tép"]:
        ws = g.check_food_text(mon, p)
        assert "ALLERGEN" in _codes(ws), mon
        assert ws[0]["level"] == "DANGER"


def test_di_ung_an_qua_gia_vi():
    # Mắm tôm → giáp xác; nước mắm → cá; dầu hào → nhuyễn thể; mayonnaise → trứng
    assert "ALLERGEN" in _codes(g.check_food_text("Bún đậu mắm tôm", GuardProfile(allergens=("Hải sản có vỏ",))))
    assert "ALLERGEN" in _codes(g.check_food_text("Rau muống xào, chấm nước mắm", GuardProfile(allergens=("Cá",))))
    assert "ALLERGEN" in _codes(g.check_food_text("Cải thìa xào dầu hào", GuardProfile(allergens=("Hải sản có vỏ",))))
    assert "ALLERGEN" in _codes(g.check_food_text("Salad sốt mayonnaise", GuardProfile(allergens=("Trứng",))))
    assert "ALLERGEN" in _codes(g.check_food_text("Bánh mì ốp la", GuardProfile(allergens=("Gluten",))))


def test_thong_diep_neu_ro_ly_do():
    ws = g.check_food_text("Tôm rang thịt", GuardProfile(allergens=("Hải sản có vỏ",)))
    assert "tôm" in ws[0]["message"]
    assert "Hải sản có vỏ" in ws[0]["message"]


def test_khong_bao_dong_gia_voi_tu_gan_giong():
    # "cà" khác "cá"; "sữa đậu nành" không phải sữa bò; "bò bía" không có thịt bò;
    # "mì Quảng" làm từ bột gạo; "trứng gà" không phải thịt gà
    assert g.check_food_text("Cà tím nướng mỡ hành", GuardProfile(allergens=("Cá",))) == []
    assert g.check_food_text("Sữa đậu nành không đường", GuardProfile(allergens=("Sữa bò",))) == []
    assert g.check_food_text("Bò bía", GuardProfile(allergens=("Thịt bò",))) == []
    assert g.check_food_text("Mì Quảng gà", GuardProfile(allergens=("Gluten",))) == []
    assert g.check_food_text("Trứng gà luộc", GuardProfile(allergens=("Thịt gà",))) == []


def test_di_ung_tu_khai_bao_tu_do():
    # Người dùng gõ "tôm" ở ô tự khai báo → hiểu là nhóm giáp xác
    p = GuardProfile(allergens=("tôm",))
    assert "ALLERGEN" in _codes(g.check_food_text("Cua rang me", p))
    # Dị nguyên lạ không có trong từ điển → khớp nguyên văn
    p2 = GuardProfile(allergens=("Kiwi",))
    assert "ALLERGEN" in _codes(g.check_food_text("Sinh tố kiwi", p2))


def test_di_nguyen_khong_phai_thuc_pham_bi_bo_qua():
    p = GuardProfile(allergens=("Phấn hoa", "Penicillin", "Bụi nhà"))
    assert g.check_food_text("Phở bò", p) == []


# ---------- Bệnh nền ----------

def test_gout_han_che_noi_tang_va_hai_san():
    p = GuardProfile(conditions=("Bệnh gout",))
    ws = g.check_food_text("Cháo lòng heo", p)
    assert _codes(ws) == ["CONDITION"]
    assert ws[0]["level"] == "WARNING"
    assert ws[0]["source"]        # mỗi rule phải có nguồn tham khảo
    assert "CONDITION" in _codes(g.check_food_text("Mực xào cần tỏi", p))


def test_dai_thao_duong_han_che_do_ngot():
    p = GuardProfile(conditions=("Đái tháo đường típ 2",))
    assert "CONDITION" in _codes(g.check_food_text("Chè đậu đen", p))
    assert "CONDITION" in _codes(g.check_food_text("Trà sữa trân châu", p))
    assert g.check_food_text("Sữa chua không đường", p) == []


def test_tang_huyet_ap_han_che_do_man():
    p = GuardProfile(conditions=("Tăng huyết áp",))
    assert "CONDITION" in _codes(g.check_food_text("Cơm, dưa muối, cá khô", p))
    assert "CONDITION" in _codes(g.check_food_text("Mì gói xúc xích", p))


def test_benh_khong_co_rule_thi_im_lang():
    assert g.check_food_text("Lòng heo", GuardProfile(conditions=("Rối loạn lo âu",))) == []


# ---------- Lộ trình 7 ngày ----------

def _plan(meals_per_day):
    return {"days": [
        {"meals": meals, "exercise": {"name": "Đi bộ", "duration_min": 30, "calories_kcal": 120}}
        for meals in meals_per_day
    ]}


def test_check_plan_gom_canh_bao_trung_lap_va_ghi_vi_tri():
    meals = [
        {"type": "Sáng", "name": "Bánh cuốn", "kcal": 400},
        {"type": "Trưa", "name": "Cơm tôm rim", "kcal": 600},
        {"type": "Tối", "name": "Canh rau", "kcal": 500},
    ]
    p = GuardProfile(gender="FEMALE", allergens=("Hải sản có vỏ",), daily_kcal_target=1500)
    ws = g.check_plan(_plan([meals, meals]), p)
    allergen = [w for w in ws if w["code"] == "ALLERGEN"]
    assert len(allergen) == 1                       # gom 2 ngày thành 1 cảnh báo
    assert allergen[0]["context"] == "Trưa · ngày 1-2"


def test_check_plan_bat_ngay_qua_it_calo():
    it = [{"type": "Sáng", "name": "Cháo", "kcal": 300},
          {"type": "Trưa", "name": "Cơm", "kcal": 400},
          {"type": "Tối", "name": "Canh", "kcal": 300}]
    ws = g.check_plan(_plan([it]), GuardProfile(gender="MALE", daily_kcal_target=2000))
    low = [w for w in ws if w["code"] == "KCAL_LOW"]
    assert low and low[0]["level"] == "DANGER"
    assert low[0]["context"] == "ngày 1"


def test_check_plan_chi_tieu_ngay_qua_thap():
    ws = g.check_plan(_plan([]), GuardProfile(gender="MALE", daily_kcal_target=1300))
    assert "TARGET_LOW" in _codes(ws)


def test_check_plan_chiu_duoc_noi_dung_hong():
    assert g.check_plan({}, GuardProfile()) == []
    assert g.check_plan(None, GuardProfile()) == []
    assert g.check_plan({"days": [{"meals": None}]}, GuardProfile()) == []


def test_canh_bao_sap_xep_nguy_hiem_truoc():
    meals = [{"type": "Sáng", "name": "Chè", "kcal": 200},
             {"type": "Trưa", "name": "Tôm hấp", "kcal": 300},
             {"type": "Tối", "name": "Canh", "kcal": 300}]
    p = GuardProfile(gender="FEMALE", allergens=("Hải sản có vỏ",),
                     conditions=("Đái tháo đường típ 2",), daily_kcal_target=1500)
    ws = g.check_plan(_plan([meals]), p)
    order = [w["level"] for w in ws]
    assert order == sorted(order, key=g.LEVEL_ORDER.index)


# ---------- Kết quả quét ảnh ----------

def _scan(**kw):
    base = {"is_food_image": True, "food_probability": 0.95, "food_name": "Phở gà",
            "calories_kcal": 450, "description": "", "confidence": 0.9}
    base.update(kw)
    return base


def test_scan_vung_tin_cay():
    p = GuardProfile()
    assert g.check_meal_scan(_scan(confidence=0.9), p) == []
    mid = g.check_meal_scan(_scan(confidence=0.5), p)
    assert _codes(mid) == ["LOW_CONFIDENCE"] and mid[0]["level"] == "WARNING"
    low = g.check_meal_scan(_scan(confidence=0.2), p)
    assert _codes(low) == ["LOW_CONFIDENCE"] and low[0]["level"] == "DANGER"


def test_scan_di_ung_trong_mo_ta():
    p = GuardProfile(allergens=("Hải sản có vỏ",))
    ws = g.check_meal_scan(_scan(food_name="Bún riêu", description="Có tôm khô và chả cua"), p)
    assert "ALLERGEN" in _codes(ws)


def test_scan_vuot_chi_tieu_ngay():
    p = GuardProfile(daily_kcal_target=2000)
    ws = g.check_meal_scan(_scan(calories_kcal=700), p, consumed_today=1800)
    assert "KCAL_HIGH" in _codes(ws)
    assert g.check_meal_scan(_scan(calories_kcal=300), p, consumed_today=1800) == []


def test_scan_khong_phai_mon_an_thi_khong_canh_bao():
    assert g.check_meal_scan({"is_food_image": False, "confidence": 0.0}, GuardProfile()) == []


# ---------- Câu trả lời chat ----------

def test_chat_nhac_toi_di_nguyen():
    p = GuardProfile(allergens=("Đậu phộng",))
    ws = g.check_chat_reply("Bạn có thể ăn gỏi cuốn chấm tương đậu phộng.", p, citation_count=2)
    assert _codes(ws) == ["ALLERGEN"]
    assert ws[0]["level"] == "WARNING"   # chat có thể đang dặn "tránh" → vàng, không đỏ


def test_chat_khong_co_trich_dan():
    ws = g.check_chat_reply("Uống đủ nước mỗi ngày.", GuardProfile(), citation_count=0)
    assert _codes(ws) == ["NO_GROUNDING"]
    assert ws[0]["level"] == "INFO"


def test_chat_cum_tu_ca_nhan_khong_phai_ca():
    ws = g.check_chat_reply("Thực đơn được cá nhân hóa cho bạn.", GuardProfile(allergens=("Cá",)), 1)
    assert ws == []


def test_vi_tri_gom_gon_theo_bua_va_khoang_ngay():
    # 7 ngày cùng món → "Trưa · ngày 1-7" thay vì liệt kê 7 lần
    meals = [{"type": "Sáng", "name": "Phở bò", "kcal": 500},
             {"type": "Trưa", "name": "Cơm gà", "kcal": 600},
             {"type": "Tối", "name": "Salad ức gà", "kcal": 500}]
    p = GuardProfile(gender="FEMALE", allergens=("Thịt gà",), daily_kcal_target=1600)
    ws = g.check_plan(_plan([meals] * 7), p)
    assert ws[0]["context"] == "Trưa, Tối · ngày 1-7"


def test_gom_ngay_khong_lien_tuc():
    assert g.compact_contexts([(1, "Trưa"), (2, "Trưa"), (3, "Trưa"), (5, "Trưa"), (5, "Tối")]) \
        == "Trưa · ngày 1-3, 5; Tối · ngày 5"
    assert g.compact_contexts([(2, None)]) == "ngày 2"

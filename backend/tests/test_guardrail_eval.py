"""Test hàm tính chỉ số đánh giá Warning Engine (kế hoạch v2, mục 5 - Guardrails)."""
import pytest

from app.services import guardrail_eval as ge


def _fake_check(case):
    # Giả lập: chỉ bắt được dị ứng khi text có chữ "tôm"
    return {"ALLERGEN"} if "tôm" in case["text"] else set()


CASES = [
    {"id": "tp", "text": "Tôm hấp", "expect": ["ALLERGEN"]},        # bắt đúng
    {"id": "fn", "text": "Bún bò Huế", "expect": ["ALLERGEN"]},     # bỏ sót (mắm ruốc ẩn)
    {"id": "fp", "text": "Cá tôm giả chay", "expect": []},          # báo nhầm
    {"id": "tn", "text": "Rau luộc", "expect": []},                 # im lặng đúng
]


def test_evaluate_cases_tinh_dung_tp_fp_fn_tn():
    cases = [{**c, "text": c["text"].lower()} for c in CASES]
    r = ge.evaluate_cases(cases, _fake_check, codes=("ALLERGEN",))
    m = r["metrics"]["ALLERGEN"]
    assert (m["tp"], m["fp"], m["fn"], m["tn"]) == (1, 1, 1, 1)
    assert m["precision"] == pytest.approx(0.5)
    assert m["recall"] == pytest.approx(0.5)
    assert m["false_alarm_rate"] == pytest.approx(0.5)
    assert [x["id"] for x in r["misses"]] == ["fn"]
    assert [x["id"] for x in r["false_alarms"]] == ["fp"]


def test_khong_co_mau_duong_thi_chi_so_bang_0_khong_chia_cho_0():
    r = ge.evaluate_cases([{"id": "a", "text": "x", "expect": []}], lambda c: set(), codes=("ALLERGEN",))
    m = r["metrics"]["ALLERGEN"]
    assert m["recall"] == 0.0 and m["precision"] == 0.0 and m["false_alarm_rate"] == 0.0


def test_check_case_dung_warning_engine_that():
    case = {"text": "Bún đậu mắm tôm", "allergens": ["Hải sản có vỏ"], "conditions": []}
    assert ge.check_case(case) == {"ALLERGEN"}


def test_khoang_tin_cay_wilson():
    lo, hi = ge.wilson_interval(16, 18)
    assert round(lo, 3) == 0.672 and round(hi, 3) == 0.969
    assert ge.wilson_interval(0, 13)[0] == 0.0
    assert ge.wilson_interval(0, 0) == (0.0, 0.0)


def test_chi_dem_ca_co_khai_bao_loai_tuong_ung():
    cases = [
        {"id": "1", "text": "Tôm rang", "allergens": ["Hải sản có vỏ"], "expect": ["ALLERGEN"]},
        {"id": "2", "text": "Rau muống luộc", "allergens": ["Hải sản có vỏ"], "expect": []},
        {"id": "3", "text": "Rau muống luộc", "conditions": ["Bệnh gout"], "expect": []},
    ]
    out = ge.applicable_counts(cases)
    assert out["ALLERGEN"] == {"pos": 1, "tp": 1, "neg": 1, "fp": 0}
    assert out["CONDITION"] == {"pos": 0, "tp": 0, "neg": 1, "fp": 0}

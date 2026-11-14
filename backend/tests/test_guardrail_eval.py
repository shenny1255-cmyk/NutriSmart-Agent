"""Test hàm tính chỉ số đánh giá Warning Engine (kế hoạch v2, mục 5 — Guardrails)."""
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

"""Bảng chi phí vận hành (GĐ1): công thức tính phải đúng và khớp số đo token."""
import importlib.util
from pathlib import Path

import pytest

_p = Path(__file__).resolve().parents[1] / "scripts" / "operating_cost.py"
_spec = importlib.util.spec_from_file_location("operating_cost", _p)
oc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(oc)  # type: ignore[union-attr]


def test_chi_phi_moi_request():
    # 1M token vào × $0.30 + 1M token ra × $2.50
    assert oc.cost_per_request(1_000_000, 1_000_000, "gemini-3.5-flash-lite") == pytest.approx(2.80)
    assert oc.cost_per_request(1514, 374, "gemini-3.5-flash-lite") == pytest.approx(0.0013892, rel=1e-4)


def test_chi_phi_thang_tang_tuyen_tinh_theo_so_nguoi_dung():
    one = oc.monthly_cost_per_user("gemini-3.5-flash-lite")
    assert one > 0
    assert oc.monthly_cost(100, "gemini-3.5-flash-lite") == pytest.approx(one * 100)


def test_moi_tac_vu_deu_co_so_do_va_tan_suat():
    assert set(oc.TASKS) == set(oc.USAGE_PER_USER_MONTH)
    for t in oc.TASKS.values():
        assert t["tokens_in"] > 0 and t["tokens_out"] > 0 and t["basis"]

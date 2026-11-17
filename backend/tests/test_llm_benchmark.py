"""Test hàm thống kê cho script đo độ trễ AI (scripts/llm_benchmark.py)."""
import importlib.util
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location(
    "llm_benchmark", Path(__file__).resolve().parents[1] / "scripts" / "llm_benchmark.py")
bm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bm)


def test_percentile_noi_suy_tuyen_tinh():
    xs = [1.0, 2.0, 3.0, 4.0]
    assert bm.percentile(xs, 50) == pytest.approx(2.5)
    assert bm.percentile(xs, 95) == pytest.approx(3.85)
    assert bm.percentile([7.0], 95) == 7.0


def test_tom_tat_mot_nhom_do():
    s = bm.summarize([2.0, 1.0, 3.0], ok=3, total=4)
    assert s["n_ok"] == 3 and s["n"] == 4
    assert s["p50"] == pytest.approx(2.0) and s["max"] == 3.0


def test_tom_tat_khi_moi_lan_deu_loi():
    s = bm.summarize([], ok=0, total=3)
    assert s["p50"] is None and s["n_ok"] == 0

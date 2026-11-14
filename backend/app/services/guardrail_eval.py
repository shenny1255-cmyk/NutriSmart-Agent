"""Đánh giá Warning Engine trên bộ test case cố định (kế hoạch ĐATN v2, mục 5 — Guardrails).

Mỗi case: {id, text, allergens, conditions, expect: [mã cảnh báo kỳ vọng], note?}
Chỉ số cho từng mã (ALLERGEN, CONDITION): precision, recall, tỷ lệ báo động giả.
Script chạy và ghi báo cáo: scripts/guardrail_eval.py
"""
from __future__ import annotations

from collections.abc import Callable

from app.services import guardrails
from app.services.guardrails import GuardProfile

CODES = ("ALLERGEN", "CONDITION")


def check_case(case: dict) -> set[str]:
    """Mã cảnh báo Warning Engine bật ra cho một món (check_food_text)."""
    profile = GuardProfile(
        allergens=tuple(case.get("allergens") or ()),
        conditions=tuple(case.get("conditions") or ()),
    )
    return {w["code"] for w in guardrails.check_food_text(case["text"], profile)}


def _ratio(a: int, b: int) -> float:
    return a / b if b else 0.0


def evaluate_cases(cases: list[dict], check: Callable[[dict], set[str]] = check_case,
                   codes: tuple[str, ...] = CODES) -> dict:
    counts = {c: {"tp": 0, "fp": 0, "fn": 0, "tn": 0} for c in codes}
    misses, false_alarms = [], []
    for case in cases:
        fired = check(case)
        expected = set(case.get("expect") or [])
        for code in codes:
            hit, want = code in fired, code in expected
            key = "tp" if hit and want else "fp" if hit else "fn" if want else "tn"
            counts[code][key] += 1
        if expected - fired:
            misses.append({**case, "fired": sorted(fired)})
        if fired - expected:
            false_alarms.append({**case, "fired": sorted(fired)})

    metrics = {}
    for code, n in counts.items():
        metrics[code] = {
            **n,
            "precision": _ratio(n["tp"], n["tp"] + n["fp"]),
            "recall": _ratio(n["tp"], n["tp"] + n["fn"]),
            "false_alarm_rate": _ratio(n["fp"], n["fp"] + n["tn"]),
        }
    return {"n": len(cases), "metrics": metrics, "misses": misses, "false_alarms": false_alarms}

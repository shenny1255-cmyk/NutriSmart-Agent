"""Đánh giá Warning Engine trên bộ test case cố định (kế hoạch ĐATN v2, mục 5 - Guardrails).

Mỗi case: {id, text, allergens, conditions, expect: [mã cảnh báo kỳ vọng], note?}
Chỉ số cho từng mã (ALLERGEN, CONDITION): precision, recall, tỷ lệ báo động giả.
Script chạy và ghi báo cáo: scripts/guardrail_eval.py
"""
from __future__ import annotations

import math
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


def wilson_interval(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Khoảng tin cậy Wilson 95% cho tỷ lệ k/n (dùng được cả khi k = 0 hoặc k = n)."""
    if n == 0:
        return 0.0, 0.0
    p = k / n
    d = 1 + z * z / n
    center = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, center - half), min(1.0, center + half)


def applicable_counts(cases: list[dict], check: Callable[[dict], set[str]] = check_case) -> dict:
    """Đếm theo từng loại CHỈ trên ca có khai báo loại đó.

    `evaluate_cases` tính TN cả những ca không khai báo dị ứng/bệnh nền tương ứng, các ca đó
    không thể báo nhầm nên làm tỷ lệ báo động giả trông tốt hơn thực tế.
    """
    fields = {"ALLERGEN": "allergens", "CONDITION": "conditions"}
    out = {}
    for code, field in fields.items():
        scoped = [c for c in cases if c.get(field)]
        pos = [c for c in scoped if code in (c.get("expect") or [])]
        neg = [c for c in scoped if code not in (c.get("expect") or [])]
        out[code] = {"pos": len(pos), "tp": sum(code in check(c) for c in pos),
                     "neg": len(neg), "fp": sum(code in check(c) for c in neg)}
    return out


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

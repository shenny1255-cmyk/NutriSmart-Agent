"""Đánh giá Warning Engine trên bộ dev + holdout, có/không bảng món → eval/results/guardrail_report.md.

Không cần DB hay LLM. Chạy từ backend/:
    PYTHONUTF8=1 ./.venv/Scripts/python.exe scripts/guardrail_eval.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.services import guardrail_eval, guardrails  # noqa: E402

SETS = [
    ("dev", BACKEND / "eval" / "guardrail_cases.json",
     "Bộ dev (73 case từ GĐ2). 13 ca bỏ sót đã được công bố trong báo cáo GĐ2 trước khi soạn "
     "bảng món, nên kết quả trên bộ này **bị lạc quan**, chỉ dùng để kiểm tra hồi quy."),
    ("holdout", BACKEND / "eval" / "guardrail_cases_holdout.json",
     "Bộ holdout (40 case, 1/3 là ca âm) viết và chốt trước khi soạn bảng món. Lưu ý trung thực: "
     "cùng một người viết holdout rồi soạn bảng món ngay sau đó, nên vẫn **chưa phải đánh giá mù**. "
     "Số liệu công bố cuối cùng cần một bộ do thành viên khác viết mà không xem bảng món."),
]
OUT = BACKEND / "eval" / "results" / "guardrail_report.md"
NAMES = {"ALLERGEN": "Dị ứng", "CONDITION": "Bệnh nền"}
HEADER = ["", "| ID | Món | Hồ sơ | Kỳ vọng | Hệ thống bật | Ghi chú |", "|---|---|---|---|---|---|"]


def _row(case: dict) -> str:
    who = ", ".join((case.get("allergens") or []) + (case.get("conditions") or []))
    return (f"| {case['id']} | {case['text']} | {who} | {', '.join(case.get('expect') or []) or '-'} "
            f"| {', '.join(case['fired']) or '-'} | {case.get('note', '')} |")


def _section(name: str, path: Path, desc: str, use_dishes: bool) -> list[str]:
    cases = json.loads(path.read_text(encoding="utf-8"))["cases"]
    with _dishes(use_dishes):
        r = guardrail_eval.evaluate_cases(cases)
    lines = [f"### {name} - {'có' if use_dishes else 'không có'} bảng món ({r['n']} case, `eval/{path.name}`)", "",
             "| Loại | TP | FP | FN | TN | Precision | Recall | Tỷ lệ báo động giả |",
             "|---|---|---|---|---|---|---|---|"]
    for code, m in r["metrics"].items():
        lines.append(f"| {NAMES.get(code, code)} | {m['tp']} | {m['fp']} | {m['fn']} | {m['tn']} "
                     f"| {m['precision']:.3f} | {m['recall']:.3f} | {m['false_alarm_rate']:.3f} |")
    if use_dishes:
        lines += ["", f"Bỏ sót: {len(r['misses'])}"] + (HEADER + [_row(c) for c in r["misses"]] if r["misses"] else [])
        lines += ["", f"Báo động giả: {len(r['false_alarms'])}"] + (
            HEADER + [_row(c) for c in r["false_alarms"]] if r["false_alarms"] else [])
    return lines + [""]


class _dishes:
    """Tạm tắt bảng món để đo baseline (chỉ từ khóa) trên cùng bộ case."""
    def __init__(self, on: bool):
        self.on = on

    def __enter__(self):
        if not self.on:
            self._orig = guardrails.match_dishes
            guardrails.match_dishes = lambda text: ()

    def __exit__(self, *exc):
        if not self.on:
            guardrails.match_dishes = self._orig


def main() -> None:
    lines = [
        "# Kết quả đánh giá Warning Engine",
        "",
        f"- Thời điểm chạy: {datetime.now():%Y-%m-%d %H:%M}",
        f"- Bảng món → nguyên liệu: {len(guardrails.load_dishes())} món (`data/dish_ingredients.json`, chưa duyệt)",
        "- Baseline \"không có guardrail\": recall = 0 cho mọi loại cảnh báo.",
        "",
    ]
    for name, path, desc in SETS:
        lines += [f"## Bộ {name}", "", desc, ""]
        lines += _section(name, path, desc, use_dishes=False)
        lines += _section(name, path, desc, use_dishes=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"\nĐã ghi → {OUT}")


if __name__ == "__main__":
    main()

"""Đánh giá Warning Engine trên bộ test case cố định → eval/results/guardrail_report.md.

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

from app.services import guardrail_eval  # noqa: E402

CASES = BACKEND / "eval" / "guardrail_cases.json"
OUT = BACKEND / "eval" / "results" / "guardrail_report.md"
NAMES = {"ALLERGEN": "Dị ứng", "CONDITION": "Bệnh nền"}


def _row(case: dict) -> str:
    who = ", ".join((case.get("allergens") or []) + (case.get("conditions") or []))
    return (f"| {case['id']} | {case['text']} | {who} | {', '.join(case.get('expect') or []) or '-'} "
            f"| {', '.join(case['fired']) or '-'} | {case.get('note', '')} |")


def main() -> None:
    cases = json.loads(CASES.read_text(encoding="utf-8"))["cases"]
    r = guardrail_eval.evaluate_cases(cases)
    lines = [
        "# Kết quả đánh giá Warning Engine",
        "",
        f"- Thời điểm chạy: {datetime.now():%Y-%m-%d %H:%M}",
        f"- Số test case: **{r['n']}** (`eval/guardrail_cases.json`)",
        "- Baseline \"không có guardrail\": recall = 0 cho mọi loại cảnh báo.",
        "",
        "| Loại | TP | FP | FN | TN | Precision | Recall | Tỷ lệ báo động giả |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for code, m in r["metrics"].items():
        lines.append(f"| {NAMES.get(code, code)} | {m['tp']} | {m['fp']} | {m['fn']} | {m['tn']} "
                     f"| {m['precision']:.3f} | {m['recall']:.3f} | {m['false_alarm_rate']:.3f} |")
    header = ["", "| ID | Món | Hồ sơ | Kỳ vọng | Hệ thống bật | Ghi chú |", "|---|---|---|---|---|---|"]
    lines += ["", f"## Bỏ sót ({len(r['misses'])})",
              "Phần lớn là **dị ứng ẩn trong tên món** - từ điển chỉ thấy chữ, không biết công thức. "
              "Hướng khắc phục: bảng món → nguyên liệu từ dữ liệu Viện Dinh dưỡng (GĐ1)."] + header
    lines += [_row(c) for c in r["misses"]]
    lines += ["", f"## Báo động giả ({len(r['false_alarms'])})"] + header
    lines += [_row(c) for c in r["false_alarms"]]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"\nĐã ghi → {OUT}")


if __name__ == "__main__":
    main()

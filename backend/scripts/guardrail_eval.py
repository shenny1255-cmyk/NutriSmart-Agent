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
EXTENDED = BACKEND / "eval" / "guardrail_cases_blind.json"
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


def _pct(k: int, n: int) -> str:
    lo, hi = guardrail_eval.wilson_interval(k, n)
    return f"{k}/{n} ({k / n:.1%}; KTC 95%: {lo:.1%} - {hi:.1%})" if n else "-"


def _extended_section() -> list[str]:
    """Bộ 40 ca đã chốt: không sửa nhãn, không sửa bảng món theo các ca bỏ sót."""
    cases = json.loads(EXTENDED.read_text(encoding="utf-8"))["cases"]
    seen = {guardrails._norm(c["text"]) for _, path, _ in SETS
            for c in json.loads(path.read_text(encoding="utf-8"))["cases"]}
    fresh = [c for c in cases if guardrails._norm(c["text"]) not in seen]
    lines = [
        "## Bộ kiểm thử mở rộng (Extended Test Set, 40 ca)",
        "",
        "- File: `eval/guardrail_cases_blind.json`, bảng chi tiết: `docs/mau_test_mu_guardrails.md`.",
        "- Nhóm chốt giữ nguyên 40 ca và 3 ca bỏ sót ngày 18/11/2026.",
        "- **Nguồn gốc theo khai báo của nhóm:** kịch bản do chuyên gia ẩm thực bên ngoài cung cấp, người viết "
        "không tiếp cận cơ sở dữ liệu của hệ thống.",
        "- **Chưa có hồ sơ đối chứng trong repo:** chưa ghi người viết, thời điểm viết và việc có dùng công cụ AI hay "
        "không; phần đầu file `docs/mau_test_mu_guardrails.md` lại ghi \"thành viên độc lập trong nhóm\". "
        "Vì vậy báo cáo này chưa gọi đây là đánh giá mù.",
        "",
        "| Chỉ số (chỉ tính ca có khai báo loại tương ứng) | Chỉ dò từ khóa | Có bảng món |",
        "|---|---|---|",
    ]
    with _dishes(False):
        base = guardrail_eval.applicable_counts(cases)
    full = guardrail_eval.applicable_counts(cases)
    for code, name in NAMES.items():
        lines.append(f"| {name}: recall | {_pct(base[code]['tp'], base[code]['pos'])} "
                     f"| {_pct(full[code]['tp'], full[code]['pos'])} |")
        lines.append(f"| {name}: báo nhầm trên ca an toàn | {_pct(base[code]['fp'], base[code]['neg'])} "
                     f"| {_pct(full[code]['fp'], full[code]['neg'])} |")
    tp = sum(v["tp"] for v in full.values())
    pos = sum(v["pos"] for v in full.values())
    fp = sum(v["fp"] for v in full.values())
    neg = sum(v["neg"] for v in full.values())
    rest = guardrail_eval.applicable_counts(fresh)
    r_tp = sum(v["tp"] for v in rest.values())
    r_pos = sum(v["pos"] for v in rest.values())
    lines += [
        f"| **Tổng: recall** | | **{_pct(tp, pos)}** |",
        f"| **Tổng: báo nhầm trên ca an toàn** | | **{_pct(fp, neg)}** |",
        "",
        "### Hạn chế cần nêu trong khóa luận",
        "",
        f"- {len(cases) - len(fresh)}/{len(cases)} tên món trùng với bộ dev/holdout; bỏ các ca trùng thì recall là "
        f"{_pct(r_tp, r_pos)}.",
        "- Tỷ lệ 18 ca dị ứng, 9 ca bệnh nền, 13 ca an toàn trùng với bộ holdout.",
        "- Mẫu nhỏ nên khoảng tin cậy rộng; 0 báo nhầm trên 13 ca chưa chứng minh được tỷ lệ báo nhầm bằng 0.",
        "- Bảng món và bảng thành phần thực phẩm vẫn ở trạng thái `CHUA_DUYET` trong dữ liệu.",
        "",
    ]
    r = guardrail_eval.evaluate_cases(cases)
    lines += [f"### Bỏ sót ({len(r['misses'])})"] + HEADER + [_row(c) for c in r["misses"]] + [""]
    return lines


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
    lines += _extended_section()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"\nĐã ghi → {OUT}")


if __name__ == "__main__":
    main()

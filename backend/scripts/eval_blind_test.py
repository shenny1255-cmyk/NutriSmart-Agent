"""Đánh giá Warning Engine trên bộ test độc lập 40 ca (guardrail_cases_blind.json).

Chạy từ thư mục backend/:
    PYTHONUTF8=1 ./.venv/Scripts/python.exe scripts/eval_blind_test.py
"""
import json
from pathlib import Path
import sys

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.services import guardrail_eval, guardrails

cases = json.loads((BACKEND / "eval" / "guardrail_cases_blind.json").read_text(encoding="utf-8"))["cases"]

print("=" * 70)
print("KẾT QUẢ ĐÁNH GIÁ TRÊN BỘ KIỂM THỬ ĐỘC LẬP (40 CA)")
print("=" * 70)

for with_dishes in [False, True]:
    mode_name = "CÓ BẢNG MÓN -> NGUYÊN LIỆU" if with_dishes else "KHÔNG CÓ BẢNG MÓN (CHỈ DÒ TỪ KHÓA TÊN MÓN)"
    orig = guardrails.match_dishes
    if not with_dishes:
        guardrails.match_dishes = lambda text: ()
    res = guardrail_eval.evaluate_cases(cases)
    guardrails.match_dishes = orig
    
    print(f"\n--- {mode_name} ---")
    for code in ["ALLERGEN", "CONDITION"]:
        m = res["metrics"][code]
        name = "Dị ứng" if code == "ALLERGEN" else "Bệnh nền"
        p = m["precision"]
        r = m["recall"]
        fp = m["false_alarm_rate"]
        print(f"[{name}] Precision: {p:.3f} | Recall: {r:.3f} | Tỷ lệ báo động giả: {fp:.3f} (Đúng: {m['tp']}, Báo nhầm: {m['fp']}, Bỏ sót: {m['fn']})")

print("\n" + "=" * 70)
print("CHI TIẾT CÁC CA BỎ SÓT (MISSES) KHI CÓ BẢNG MÓN:")
print("=" * 70)
orig = guardrails.match_dishes
res = guardrail_eval.evaluate_cases(cases)
guardrails.match_dishes = orig
for m in res["misses"]:
    who = ", ".join(m.get("allergens", []) + m.get("conditions", []))
    print(f"- ID {m['id']}: '{m['text']}' | Nhóm: {who} | Kỳ vọng: {m['expect']} | Thực tế: {m['fired'] or 'KHÔNG'}")
    print(f"  Lý do: {m.get('note', '')}")

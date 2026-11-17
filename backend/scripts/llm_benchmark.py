"""Đo độ trễ p50/p95 và số token của từng nhà cung cấp AI (kế hoạch ĐATN v2, mục 2.2).

Đo thực tế thay cho con số cam kết trước. Gọi thẳng các hàm provider trong services/llm.py
(không ghi audit, không ẩn danh vì prompt đo đạc không chứa dữ liệu người dùng).

Chạy từ backend/ (Ollama cần đang chạy; Gemini cần GEMINI_API_KEY):
    PYTHONUTF8=1 ./.venv/Scripts/python.exe scripts/llm_benchmark.py
    PYTHONUTF8=1 ./.venv/Scripts/python.exe scripts/llm_benchmark.py --providers gemini --chat-runs 10 --plan-runs 3

Kết quả: eval/results/llm_benchmark.md
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

OUT = BACKEND / "eval" / "results" / "llm_benchmark.md"

# Prompt cố định, không chứa dữ liệu cá nhân → lặp lại được giữa các lần đo.
CHAT_SYSTEM = ("Bạn là trợ lý dinh dưỡng NutriSmart. Hồ sơ: Giới tính MALE · Tuổi 25-34 · "
               "Cao 170cm · Nặng 72kg · Bệnh nền: Bệnh gout · Mục tiêu 2000 kcal/ngày.")
CHAT_QUESTION = "Người bệnh gout nên ăn gì vào bữa sáng? Trả lời ngắn gọn 3-4 câu."


# ---------- Thống kê (hàm thuần, có test) ----------

def percentile(values: list[float], p: float) -> float:
    """Phân vị có nội suy tuyến tính (giống numpy mặc định)."""
    xs = sorted(values)
    if len(xs) == 1:
        return xs[0]
    k = (len(xs) - 1) * p / 100
    lo = int(k)
    hi = min(lo + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


def summarize(latencies: list[float], ok: int, total: int) -> dict:
    if not latencies:
        return {"n": total, "n_ok": ok, "p50": None, "p95": None, "max": None}
    return {"n": total, "n_ok": ok, "p50": percentile(latencies, 50),
            "p95": percentile(latencies, 95), "max": max(latencies)}


# ---------- Đo ----------

def _run(provider: str, task: str):
    """Một lần gọi → (giây, usage | None). Ném lỗi nếu thất bại."""
    from app.config import settings
    from app.services import llm, plan_generator

    if task == "chat":
        messages = [{"role": "system", "content": CHAT_SYSTEM}, {"role": "user", "content": CHAT_QUESTION}]
        kwargs = {"max_tokens": 400}
    else:   # plan: sinh lộ trình 7 ngày JSON theo schema - tác vụ nặng nhất của hệ thống
        profile = {"gender": "MALE", "age": "25-34", "height_cm": 170, "weight_kg": 72, "bmi": 24.9,
                   "goal": "LOSE_WEIGHT", "conditions": ["Bệnh gout"], "allergens": ["Đậu phộng"]}
        messages = [{"role": "user", "content": plan_generator.build_prompt(profile, 1800)}]
        kwargs = {"max_tokens": 2048, "temperature": 0,
                  "json_schema": plan_generator.PlanOutput.model_json_schema()}

    t0 = time.perf_counter()
    if provider == "ollama":
        model = settings.OLLAMA_CHAT_MODEL if task == "chat" else settings.OLLAMA_MODEL
        opts = {"num_ctx": 4096} if task == "plan" else None
        text = llm._ollama_chat(messages, model=model, timeout=settings.PLAN_LLM_TIMEOUT_SECONDS,
                                ollama_options=opts, **kwargs)
        usage = None
    else:
        text, usage = llm._gemini_chat(messages, timeout=settings.PLAN_LLM_TIMEOUT_SECONDS, **kwargs)
    secs = time.perf_counter() - t0
    if task == "plan":
        plan_generator.PlanOutput.model_validate_json(plan_generator._strip_fence(text))  # phải hợp lệ
    return secs, usage


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--providers", default="ollama,gemini")
    ap.add_argument("--chat-runs", type=int, default=5)
    ap.add_argument("--plan-runs", type=int, default=1)
    args = ap.parse_args()

    from app.config import settings
    rows, notes = [], []
    for provider in [p.strip() for p in args.providers.split(",") if p.strip()]:
        for task, runs in (("chat", args.chat_runs), ("plan", args.plan_runs)):
            lat, tokens_in, tokens_out, models, ok = [], [], [], set(), 0
            for i in range(runs):
                try:
                    secs, usage = _run(provider, task)
                    lat.append(secs)
                    ok += 1
                    if usage:
                        models.add(usage.get("model"))
                        if usage.get("prompt_tokens"):
                            tokens_in.append(usage["prompt_tokens"])
                        if usage.get("output_tokens"):
                            tokens_out.append(usage["output_tokens"])
                    print(f"[{provider}/{task}] lần {i + 1}: {secs:.2f}s")
                except Exception as e:  # noqa: BLE001 - ghi nhận lỗi vào báo cáo, đo tiếp
                    notes.append(f"{provider}/{task} lần {i + 1}: {type(e).__name__}: {str(e)[:160]}")
                    print(f"[{provider}/{task}] lần {i + 1}: LỖI {e}")
            model = (", ".join(sorted(m for m in models if m)) if provider == "gemini"
                     else (settings.OLLAMA_CHAT_MODEL if task == "chat" else settings.OLLAMA_MODEL))
            rows.append({"provider": provider, "task": task, "model": model, **summarize(lat, ok, runs),
                         "tok_in": sum(tokens_in) / len(tokens_in) if tokens_in else None,
                         "tok_out": sum(tokens_out) / len(tokens_out) if tokens_out else None})

    f = lambda v, d=2: "-" if v is None else f"{v:.{d}f}"  # noqa: E731
    lines = [
        "# Đo độ trễ và token theo nhà cung cấp AI",
        "",
        f"- Thời điểm đo: {datetime.now():%Y-%m-%d %H:%M} · máy chạy backend: máy phát triển của nhóm",
        "- `chat`: câu hỏi tư vấn ngắn kèm hồ sơ · `plan`: sinh lộ trình 7 ngày JSON theo schema (đã kiểm tra hợp lệ)",
        "- Ollama chạy trên chính máy phát triển (CPU), chưa phải GPU server; Gemini gọi qua Internet.",
        "",
        "| Provider | Tác vụ | Model | Thành công | p50 (s) | p95 (s) | Max (s) | Token vào TB | Token ra TB |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(f"| {r['provider']} | {r['task']} | {r['model']} | {r['n_ok']}/{r['n']} | {f(r['p50'])} "
                     f"| {f(r['p95'])} | {f(r['max'])} | {f(r['tok_in'], 0)} | {f(r['tok_out'], 0)} |")
    lines += ["", "Số token dùng để điền bảng chi phí vận hành (mục 2.2 kế hoạch): "
              "chi phí/request = token vào × đơn giá vào + token ra × đơn giá ra (tra bảng giá hiện hành)."]
    if notes:
        lines += ["", "## Lỗi ghi nhận khi đo", ""] + [f"- {n}" for n in notes]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"\nĐã ghi → {OUT}")
    _ = json  # giữ import cho người mở rộng script xuất JSON


if __name__ == "__main__":
    main()

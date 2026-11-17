"""Bảng chi phí vận hành AI đám mây (kế hoạch ĐATN v2, mục 2.2 - GĐ1).

Chi phí/request = token vào × đơn giá vào + token ra × đơn giá ra.
- Đơn giá: bảng giá Gemini Developer API (Paid tier, Standard), tra ngày 17/11/2026.
- Token: ĐO THẬT trên hệ thống (audit_logs / usage_metadata), trừ dòng ghi "ước lượng".
- Tần suất dùng: GIẢ ĐỊNH, ghi rõ để hội đồng có thể đổi và tính lại.

Chạy từ backend/:  PYTHONUTF8=1 ./.venv/Scripts/python.exe scripts/operating_cost.py
Kết quả: eval/results/operating_cost.md
"""
from __future__ import annotations

from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "eval" / "results" / "operating_cost.md"

PRICE_SOURCE = "https://ai.google.dev/gemini-api/docs/pricing (Paid tier, Standard, tra ngày 17/11/2026)"
# USD / 1 triệu token: (vào, ra - đã gồm thinking token)
PRICES = {
    "gemini-3.5-flash-lite": (0.30, 2.50),   # model mặc định của hệ thống
    "gemini-3.1-flash-lite": (0.25, 1.50),   # model dự phòng thứ 2
    "gemini-2.5-flash-lite": (0.10, 0.40),   # model dự phòng thứ 3
}
DEFAULT_MODEL = "gemini-3.5-flash-lite"
USD_VND = 25_950   # Vietcombank, giá bán USD ngày 17/11/2026

TASKS = {
    "chat": {"name": "Chat tư vấn (kèm RAG + lịch sử)", "tokens_in": 1514, "tokens_out": 374,
             "basis": "đo thật: TB 7 lượt chat qua API (audit_logs), độ trễ trung vị ~2,9 s"},
    "meal_scan": {"name": "Phân tích ảnh món ăn", "tokens_in": 1513, "tokens_out": 162,
                  "basis": "đo thật: 3 ảnh mẫu (usage_metadata); ảnh ~1.090 token + prompt 424 token, ~2,3 s"},
    "plan_generate": {"name": "Sinh lộ trình 7 ngày (JSON)", "tokens_in": 601, "tokens_out": 1202,
                      "basis": "đo thật: scripts/llm_benchmark.py (eval/results/llm_benchmark.md), ~4,9 s"},
    "feedback": {"name": "Nhận xét check-in / đánh giá chu kỳ", "tokens_in": 600, "tokens_out": 200,
                 "basis": "ước lượng (chưa đo): prompt ngắn, giới hạn 180-220 token ra"},
}

# Giả định một người dùng hoạt động trong 1 tháng (30 ngày)
USAGE_PER_USER_MONTH = {
    "chat": 90,            # 3 câu hỏi/ngày
    "meal_scan": 60,       # 2 ảnh/ngày
    "plan_generate": 5,    # 1 lộ trình mỗi chu kỳ 7 ngày + 1 lần sinh lại
    "feedback": 9,         # check-in + đánh giá mỗi chu kỳ
}
SCENARIOS = [100, 1_000, 10_000]


def cost_per_request(tokens_in: float, tokens_out: float, model: str = DEFAULT_MODEL) -> float:
    p_in, p_out = PRICES[model]
    return tokens_in * p_in / 1e6 + tokens_out * p_out / 1e6


def task_cost(task: str, model: str = DEFAULT_MODEL) -> float:
    t = TASKS[task]
    return cost_per_request(t["tokens_in"], t["tokens_out"], model)


def monthly_cost_per_user(model: str = DEFAULT_MODEL) -> float:
    return sum(task_cost(k, model) * n for k, n in USAGE_PER_USER_MONTH.items())


def monthly_cost(users: int, model: str = DEFAULT_MODEL) -> float:
    return monthly_cost_per_user(model) * users


def _usd(v: float, d: int = 4) -> str:
    return f"${v:,.{d}f}"


def _n(v: int) -> str:
    return f"{v:,}".replace(",", ".")


def _vnd(v: float) -> str:
    return f"{v * USD_VND:,.0f} đ".replace(",", ".")


def build_report() -> str:
    m = DEFAULT_MODEL
    L = [
        "# Bảng chi phí vận hành AI đám mây",
        "",
        f"- Đơn giá: {PRICE_SOURCE}",
        f"- Tỷ giá: {USD_VND:,} VND/USD (Vietcombank, giá bán ngày 17/11/2026)".replace(",", "."),
        "- Token đo trên chính hệ thống, trừ dòng ghi \"ước lượng\". Tạo lại: `scripts/operating_cost.py`.",
        "",
        f"## 1. Chi phí mỗi request ({m})",
        "",
        "| Tác vụ | Token vào | Token ra | USD/request | VND/request | Cơ sở số liệu |",
        "|---|---|---|---|---|---|",
    ]
    for k, t in TASKS.items():
        c = task_cost(k, m)
        L.append(f"| {t['name']} | {_n(t['tokens_in'])} | {_n(t['tokens_out'])} | {_usd(c, 5)} | {_vnd(c)} | {t['basis']} |")
    L += ["", "Token ra đắt hơn token vào 8 lần nên câu trả lời dài (chat, lộ trình) chiếm phần lớn chi phí.",
          "", "## 2. Chi phí theo tháng", "", "Giả định một người dùng hoạt động/tháng:", ""]
    L += [f"- {TASKS[k]['name']}: {n} lần" for k, n in USAGE_PER_USER_MONTH.items()]
    per_user = monthly_cost_per_user(m)
    L += ["", f"→ **{_usd(per_user, 3)} ≈ {_vnd(per_user)} / người dùng / tháng**", "",
          "| Người dùng hoạt động | " + " | ".join(PRICES) + " |",
          "|---|" + "---|" * len(PRICES)]
    for n in SCENARIOS:
        L.append(f"| {_n(n)} | " + " | ".join(f"{_usd(monthly_cost(n, mm), 2)} ({_vnd(monthly_cost(n, mm))})"
                                            for mm in PRICES) + " |")
    L += ["", "Cơ cấu chi phí mỗi người dùng/tháng (model mặc định):", "",
          "| Tác vụ | USD/tháng | Tỷ trọng |", "|---|---|---|"]
    for k, n in USAGE_PER_USER_MONTH.items():
        c = task_cost(k, m) * n
        L.append(f"| {TASKS[k]['name']} | {_usd(c)} | {c / per_user:.0%} |")
    L += [
        "",
        "## 3. Ghi chú để trình bày trung thực",
        "",
        "- **Gói miễn phí** (Free tier) không tốn tiền nhưng Google ghi rõ nội dung gửi lên *được dùng để cải "
        "thiện sản phẩm của Google* và giới hạn số request. Chỉ phù hợp cho demo với dữ liệu đã ẩn danh. Khi có "
        "người dùng thật nên dùng gói trả phí (nội dung *không* dùng để cải thiện sản phẩm).",
        "- **Chi phí cố định không nằm trong bảng:** máy chủ backend + PostgreSQL, và Ollama trên máy chủ vẫn cần "
        "cho embedding `bge-m3` (RAG) và làm phương án dự phòng/chế độ \"chỉ AI nội bộ\". Không cần Ollama ở máy "
        "người dùng.",
        "- **So với chạy hoàn toàn nội bộ:** Ollama (gemma3:1b) trên CPU máy phát triển mất ~17 s/câu chat và "
        "~90 s/lộ trình (eval/results/llm_benchmark.md), không phục vụ được nhiều người cùng lúc; muốn nhanh cần "
        "GPU thuê theo giờ - chi phí cố định, chưa khảo sát báo giá trong đồ án này.",
        "- **Cách giảm chi phí có sẵn trong bảng giá:** Batch API giảm 50% - hợp với job nền (nhận xét check-in, "
        "đánh giá chu kỳ) vì không cần trả lời ngay; giới hạn độ dài câu trả lời (`LLM_MAX_OUTPUT_TOKENS`).",
        "- Tần suất dùng là giả định; đổi `USAGE_PER_USER_MONTH` trong script rồi chạy lại để có bảng mới.",
    ]
    return "\n".join(L) + "\n"


def main() -> None:
    text = build_report()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding="utf-8")
    print(text)
    print(f"Đã ghi → {OUT}")


if __name__ == "__main__":
    main()

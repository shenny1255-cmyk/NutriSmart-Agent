"""Script kiểm tra ngẫu nhiên 12 nhãn RAG (Việc 1 - GĐ2 ĐATN).

Chạy:
    PYTHONUTF8=1 ./.venv/Scripts/python.exe scripts/verify_rag_labels.py

Yêu cầu: Postgres đang chạy (docker start nutrismart-db).
Kết quả ghi vào: eval/results/label_verification.md
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# 12 câu được chọn ngẫu nhiên (seed=42) từ 29 câu labeled có chunk.
# Cố định ở đây để lần chạy lại cho cùng kết quả.
# ---------------------------------------------------------------------------
SAMPLE_IDS = ["q37", "q49", "q42", "q03", "q02", "q51",
              "q41", "q05", "q09", "q14", "q18", "q35"]

EVAL_DIR   = Path(__file__).parent.parent / "eval"
RESULT_DIR = EVAL_DIR / "results"
RESULT_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Kết nối DB
# ---------------------------------------------------------------------------
try:
    import psycopg2
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur  = conn.cursor()
    DB_OK = True
except Exception as e:
    print(f"[WARN] Không kết nối được DB: {e}")
    print("[WARN] Chạy ở chế độ offline - chỉ hiện câu hỏi và nhãn, không truy vấn nội dung chunk.")
    DB_OK = False

# ---------------------------------------------------------------------------
# Đọc bộ câu hỏi
# ---------------------------------------------------------------------------
questions = {
    q["id"]: q
    for q in json.loads((EVAL_DIR / "rag_questions.json").read_text(encoding="utf-8"))["questions"]
}

def get_chunk_content(chunk_id: int) -> str:
    if not DB_OK:
        return "(offline - không lấy được nội dung)"
    cur.execute("SELECT content FROM doc_chunks WHERE id = %s", (chunk_id,))
    row = cur.fetchone()
    return row[0][:400] if row else f"(không tìm thấy chunk id={chunk_id})"

# ---------------------------------------------------------------------------
# Hiển thị và thu thập kết quả
# ---------------------------------------------------------------------------
print("=" * 70)
print("KIỂM TRA NHÃN RAG - 12 CÂU NGẪU NHIÊN (seed=42)")
print("=" * 70)
print("Với mỗi câu: đọc câu hỏi, đọc nội dung chunk, rồi nhập Đ hoặc S\n")

results = []
agree = 0

for i, qid in enumerate(SAMPLE_IDS, 1):
    q = questions[qid]
    chunk_ids = q.get("relevant_chunk_ids", [])

    print(f"\n{'─'*60}")
    print(f"[{i:02d}/12] Câu {qid}: {q['question']}")
    print(f"Lý do AI chọn: {q.get('label_reason', '(không có)')}")
    print(f"Chunk được gán nhãn: {chunk_ids}")
    print()

    for cid in chunk_ids:
        content = get_chunk_content(cid)
        print(f"  ▶ Chunk {cid}:\n    {content[:300]}{'…' if len(content) > 300 else ''}\n")

    while True:
        ans = input("  → Nhãn này đúng không? [Đ=đồng ý / S=sai / ?=không chắc]: ").strip().upper()
        if ans in ("Đ", "D", "S", "?"):
            break
        print("     Nhập Đ, S hoặc ?")

    note = ""
    if ans in ("S", "?"):
        note = input("  → Ghi chú (câu nào bị sai, chunk nào nên thêm/bớt): ").strip()

    agreed = ans in ("Đ", "D")
    if agreed:
        agree += 1

    results.append({
        "id": qid,
        "question": q["question"],
        "chunk_ids": chunk_ids,
        "verdict": "Đồng ý" if agreed else ("Không chắc" if ans == "?" else "Không đồng ý"),
        "note": note,
    })

# ---------------------------------------------------------------------------
# Ghi báo cáo
# ---------------------------------------------------------------------------
pct = agree / len(SAMPLE_IDS) * 100
report_path = RESULT_DIR / "label_verification.md"

lines = [
    "# Kết quả kiểm tra nhãn RAG",
    f"> Ngày kiểm tra: {datetime.now().strftime('%d/%m/%Y %H:%M')}  ",
    f"> Người kiểm tra: thành viên nhóm E15  ",
    f"> Phương pháp: chọn ngẫu nhiên 12/51 câu (seed=42, ~23.5%), đối chiếu thủ công với nội dung chunk trong DB.\n",
    "## Kết quả tổng hợp\n",
    f"**Đồng thuận: {agree}/{len(SAMPLE_IDS)} câu ({pct:.1f}%)**\n",
    "> Câu trích dẫn cho khóa luận:",
    f'> *"Nhãn được gán bởi mô hình AI dựa trên trích dẫn; nhóm kiểm tra ngẫu nhiên '
    f'{len(SAMPLE_IDS)}/51 câu (seed=42), đồng thuận {agree}/{len(SAMPLE_IDS)} ({pct:.1f}%)."*\n',
    "## Chi tiết từng câu\n",
    "| # | ID | Câu hỏi | Chunks | Kết quả | Ghi chú |",
    "|---|---|---|---|---|---|",
]

for i, r in enumerate(results, 1):
    chunks_str = ", ".join(str(c) for c in r["chunk_ids"])
    note_str   = r["note"] or "-"
    icon = "✅" if r["verdict"] == "Đồng ý" else ("⚠️" if r["verdict"] == "Không chắc" else "❌")
    lines.append(f"| {i} | {r['id']} | {r['question'][:55]}… | {chunks_str} | {icon} {r['verdict']} | {note_str} |")

report_path.write_text("\n".join(lines), encoding="utf-8")
print(f"\n{'='*60}")
print(f"Kết quả: đồng thuận {agree}/{len(SAMPLE_IDS)} ({pct:.1f}%)")
print(f"Báo cáo đã lưu: {report_path}")

if DB_OK:
    cur.close()
    conn.close()

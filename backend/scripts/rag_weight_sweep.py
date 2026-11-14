"""Thực nghiệm quét trọng số Hybrid RAG + hiệu chỉnh ngưỡng MIN_SCORE (kế hoạch ĐATN v2, mục 2.4.1).

Cần Postgres (kho tài liệu đã duyệt + index) và Ollama (bge-m3) đang chạy.
Chạy từ thư mục backend/:

    # 1. Xuất ứng viên để gán nhãn (mở CSV, điền 1 vào cột relevant cho đoạn liên quan)
    PYTHONUTF8=1 ./.venv/Scripts/python.exe scripts/rag_weight_sweep.py candidates

    # 2. Nạp nhãn từ CSV vào bộ câu hỏi
    PYTHONUTF8=1 ./.venv/Scripts/python.exe scripts/rag_weight_sweep.py import-labels

    # 3. Quét w = 0.0 … 1.0, so với RRF, chọn ngưỡng MIN_SCORE → eval/results/
    PYTHONUTF8=1 ./.venv/Scripts/python.exe scripts/rag_weight_sweep.py sweep

Chi tiết quy trình gán nhãn: eval/README.md
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from sqlalchemy import text  # noqa: E402

from app.database import SessionLocal  # noqa: E402
from app.services import rag_eval, retrieval  # noqa: E402
from app.services.ollama_client import get_embedding  # noqa: E402

EVAL_DIR = BACKEND / "eval"
QUESTIONS = EVAL_DIR / "rag_questions.json"
LABELS_CSV = EVAL_DIR / "rag_labels.csv"
RESULTS = EVAL_DIR / "results"

CURRENT_W = retrieval.W_VECTOR
CURRENT_MIN_SCORE = retrieval.MIN_SCORE
CANDIDATES_PER_LIST = 8      # số ứng viên lấy từ mỗi danh sách (vector / trigram / hybrid) để gán nhãn
SNIPPET = 300

# Cùng bộ lọc với services/retrieval.py, nhưng trả về điểm TỪNG thành phần của MỌI chunk
# → xếp hạng lại cho mọi w trong Python, không phải truy vấn lại DB.
_COMPONENTS_SQL = text("""
    SELECT c.id,
           c.content,
           d.title AS doc_title,
           1 - (c.embedding <=> CAST(:qvec AS vector)) AS cos,
           similarity(c.content, :q)                   AS trg
    FROM doc_chunks c
    JOIN documents d ON d.id = c.document_id
    WHERE c.embedding IS NOT NULL
      AND d.status = 'APPROVED'
      AND d.deleted_at IS NULL
""")


def load_questions(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))["questions"]


def fetch_components(db, question: str) -> list[dict]:
    qvec = get_embedding(question)
    rows = db.execute(_COMPONENTS_SQL, {"qvec": str(qvec), "q": question}).mappings().all()
    return [
        {"id": int(r["id"]), "content": r["content"], "doc_title": r["doc_title"],
         "cos": float(r["cos"] or 0.0), "trg": float(r["trg"] or 0.0)}
        for r in rows
    ]


# ---------- Bước 1: xuất ứng viên để gán nhãn ----------

def cmd_candidates(args) -> None:
    questions = load_questions(args.questions)
    out_rows = []
    with SessionLocal() as db:
        for q in questions:
            comps = fetch_components(db, q["question"])
            cands = {c["id"]: (c["cos"], c["trg"]) for c in comps}
            by_id = {c["id"]: c for c in comps}
            # Gộp top của 3 cách xếp hạng để người gán nhãn thấy đủ ứng viên, không thiên vị w nào
            pool: list[int] = []
            for ranking in (rag_eval.hybrid_ranking(cands, 1.0),
                            rag_eval.hybrid_ranking(cands, 0.0),
                            rag_eval.hybrid_ranking(cands, CURRENT_W)):
                for cid in ranking[:CANDIDATES_PER_LIST]:
                    if cid not in pool:
                        pool.append(cid)
            for cid in pool:
                c = by_id[cid]
                snippet = " ".join(c["content"].split())[:SNIPPET]
                out_rows.append({
                    "question_id": q["id"], "question": q["question"],
                    "off_topic": int(bool(q.get("off_topic"))),
                    "chunk_id": cid, "doc_title": c["doc_title"],
                    "cos": f"{c['cos']:.4f}", "trg": f"{c['trg']:.4f}",
                    "snippet": snippet,
                    "relevant": "1" if cid in set(q.get("relevant_chunk_ids") or []) else "",
                })
            print(f"[{q['id']}] {len(pool)} ứng viên")

    args.csv.parent.mkdir(parents=True, exist_ok=True)
    # utf-8-sig để Excel mở đúng tiếng Việt
    with args.csv.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()) if out_rows else ["question_id"])
        w.writeheader()
        w.writerows(out_rows)
    print(f"Đã ghi {len(out_rows)} dòng → {args.csv}")


# ---------- Bước 2: nạp nhãn ----------

def cmd_import_labels(args) -> None:
    data = json.loads(args.questions.read_text(encoding="utf-8"))
    labels: dict[str, list[int]] = {}
    seen: set[str] = set()
    with args.csv.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            seen.add(row["question_id"])
            if (row.get("relevant") or "").strip().lower() in {"1", "x", "y", "yes", "có", "co"}:
                labels.setdefault(row["question_id"], []).append(int(row["chunk_id"]))
    for q in data["questions"]:
        if q["id"] in seen:
            q["relevant_chunk_ids"] = sorted(set(labels.get(q["id"], [])))
            q["labeled"] = True
    args.questions.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    labeled = sum(1 for q in data["questions"] if q.get("relevant_chunk_ids"))
    print(f"Đã nạp nhãn: {labeled}/{len(data['questions'])} câu có đoạn liên quan → {args.questions}")


# ---------- Bước 3: quét trọng số ----------

def _svg_chart(rows: list[dict], rrf: dict, path: Path) -> None:
    """Biểu đồ đường Recall@5 / MRR / nDCG@5 theo w - SVG thuần, không cần matplotlib."""
    W, H, L, R, T, B = 640, 380, 56, 150, 24, 48
    pw, ph = W - L - R, H - T - B
    x = lambda w: L + w * pw                       # noqa: E731
    y = lambda v: T + (1 - v) * ph                 # noqa: E731
    series = [("recall@k", "Recall@5", "#2563eb"), ("mrr", "MRR", "#16a34a"),
              ("ndcg@k", "nDCG@5", "#d97706")]
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
             f'font-family="sans-serif" font-size="12">',
             f'<rect width="{W}" height="{H}" fill="#fff"/>']
    for i in range(6):
        v = i / 5
        parts.append(f'<line x1="{L}" x2="{L + pw}" y1="{y(v):.1f}" y2="{y(v):.1f}" stroke="#e5e7eb"/>')
        parts.append(f'<text x="{L - 8}" y="{y(v) + 4:.1f}" text-anchor="end" fill="#6b7280">{v:.1f}</text>')
    for r in rows:
        parts.append(f'<text x="{x(r["w"]):.1f}" y="{T + ph + 18}" text-anchor="middle" '
                     f'fill="#6b7280">{r["w"]:.1f}</text>')
    parts.append(f'<text x="{L + pw / 2}" y="{H - 8}" text-anchor="middle">'
                 f'w (trọng số vector; 1 − w cho trigram)</text>')
    cx = x(CURRENT_W)
    parts.append(f'<line x1="{cx:.1f}" x2="{cx:.1f}" y1="{T}" y2="{T + ph}" stroke="#9ca3af" '
                 f'stroke-dasharray="4 4"/>')
    parts.append(f'<text x="{cx + 4:.1f}" y="{T + 12}" fill="#6b7280">hiện tại w={CURRENT_W}</text>')
    for li, (key, label, color) in enumerate(series):
        pts = " ".join(f"{x(r['w']):.1f},{y(r[key]):.1f}" for r in rows)
        parts.append(f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="2"/>')
        for r in rows:
            parts.append(f'<circle cx="{x(r["w"]):.1f}" cy="{y(r[key]):.1f}" r="3" fill="{color}"/>')
        ry = y(rrf[key])
        parts.append(f'<line x1="{L}" x2="{L + pw}" y1="{ry:.1f}" y2="{ry:.1f}" stroke="{color}" '
                     f'stroke-dasharray="2 5" opacity="0.7"/>')
        ly = T + 10 + li * 20
        parts.append(f'<line x1="{L + pw + 14}" x2="{L + pw + 34}" y1="{ly}" y2="{ly}" '
                     f'stroke="{color}" stroke-width="2"/>')
        parts.append(f'<text x="{L + pw + 40}" y="{ly + 4}">{label}</text>')
    ly = T + 10 + len(series) * 20
    parts.append(f'<line x1="{L + pw + 14}" x2="{L + pw + 34}" y1="{ly}" y2="{ly}" stroke="#6b7280" '
                 f'stroke-dasharray="2 5"/>')
    parts.append(f'<text x="{L + pw + 40}" y="{ly + 4}">RRF (k=60)</text>')
    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def _write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow({k: (f"{v:.4f}" if isinstance(v, float) else v) for k, v in r.items()})


def cmd_sweep(args) -> None:
    questions = load_questions(args.questions)
    queries, top1_by_w = [], {}
    with SessionLocal() as db:
        for q in questions:
            comps = fetch_components(db, q["question"])
            cands = {c["id"]: (c["cos"], c["trg"]) for c in comps}
            queries.append({"id": q["id"], "off_topic": bool(q.get("off_topic")),
                            "relevant": set(q.get("relevant_chunk_ids") or []),
                            "labeled": bool(q.get("labeled")),
                            "candidates": cands})
            print(f"[{q['id']}] {len(cands)} chunk")

    k = args.k
    rows = rag_eval.sweep_weights(queries, rag_eval.DEFAULT_WEIGHTS, k)
    rrf = rag_eval.evaluate(queries, rag_eval.rrf_ranking, k)
    n = rows[0]["n"]
    if n == 0:
        sys.exit("Chưa có câu nào được gán nhãn - chạy `candidates` rồi `import-labels` trước.")

    best = rag_eval.best_row(rows, args.metric)

    # Ngưỡng: điểm top-1 hybrid (w hiện tại) của câu đúng chủ đề vs câu lạc đề
    def top1(q, w):
        if not q["candidates"]:
            return 0.0
        return max(rag_eval.hybrid_score(c, t, w) for c, t in q["candidates"].values())

    # Dương = có đoạn trả lời được; Âm = lạc đề hoặc kho không có tài liệu cho câu đó
    pos_q, neg_q = rag_eval.split_for_threshold(queries)
    on = [top1(q, CURRENT_W) for q in pos_q]
    off = [top1(q, CURRENT_W) for q in neg_q]
    thresholds = [round(0.20 + i * 0.01, 2) for i in range(41)]
    th_rows = rag_eval.threshold_sweep(on, off, thresholds) if on and off else []
    best_th = rag_eval.best_threshold(th_rows) if th_rows else None

    RESULTS.mkdir(parents=True, exist_ok=True)
    _write_csv(RESULTS / "weight_sweep.csv", rows)
    if th_rows:
        _write_csv(RESULTS / "min_score_sweep.csv", th_rows)
    _svg_chart(rows, rrf, RESULTS / "weight_sweep.svg")

    cur = next(r for r in rows if r["w"] == CURRENT_W)
    lines = [
        "# Kết quả thực nghiệm trọng số Hybrid RAG",
        "",
        f"- Thời điểm chạy: {datetime.now():%Y-%m-%d %H:%M}",
        f"- Số câu có đoạn liên quan: **{n}** / {len(queries)}; câu không nên trích dẫn (lạc đề hoặc kho không có tài liệu): {len(off)}",
        f"- Chỉ số chọn w tốt nhất: `{args.metric}`, k = {k}",
        "",
        "| Cấu hình | Recall@k | MRR | nDCG@k |",
        "|---|---|---|---|",
    ]
    for r in rows:
        tag = " ← hiện tại" if r["w"] == CURRENT_W else ""
        tag += " ★ tốt nhất" if r is best else ""
        name = {0.0: "Pure Trigram (w=0.0)", 1.0: "Pure Vector (w=1.0)"}.get(r["w"], f"Hybrid w={r['w']}")
        lines.append(f"| {name}{tag} | {r['recall@k']:.3f} | {r['mrr']:.3f} | {r['ndcg@k']:.3f} |")
    lines.append(f"| RRF (k={rag_eval.RRF_K}) | {rrf['recall@k']:.3f} | {rrf['mrr']:.3f} | {rrf['ndcg@k']:.3f} |")
    lines += [
        "",
        f"**Kết luận tự động:** w tốt nhất theo {args.metric} = **{best['w']}** "
        f"({best[args.metric]:.3f}); w hiện tại {CURRENT_W} đạt {cur[args.metric]:.3f}. "
        + ("Có bằng chứng giữ nguyên trọng số." if best["w"] == CURRENT_W
           else "Cân nhắc đổi `W_VECTOR` trong `services/retrieval.py` theo kết quả này "
                "(nhớ kiểm tra độ chênh có đáng kể không với cỡ mẫu hiện tại)."),
        "",
    ]
    # Kiểm định: chênh lệch giữa w tốt nhất và w hiện tại có vượt nhiễu không (paired bootstrap)
    metric = args.metric
    pq_best = rag_eval.per_query(queries, lambda c: rag_eval.hybrid_ranking(c, best["w"]), k)
    pq_cur = rag_eval.per_query(queries, lambda c: rag_eval.hybrid_ranking(c, CURRENT_W), k)
    pq_rrf = rag_eval.per_query(queries, rag_eval.rrf_ranking, k)
    lines += ["", f"### Kiểm định paired bootstrap ({metric}, 10.000 lần lấy mẫu, CI 95%)", "",
              "| So sánh | Hiệu TB | CI 95% | Có ý nghĩa? |", "|---|---|---|---|"]
    for name, a, b in ((f"w={best['w']} vs w={CURRENT_W}", pq_best, pq_cur),
                       (f"w={CURRENT_W} vs RRF", pq_cur, pq_rrf)):
        bs = rag_eval.paired_bootstrap([r[metric] for r in a], [r[metric] for r in b])
        lines.append(f"| {name} | {bs['mean_diff']:+.3f} | [{bs['ci_low']:+.3f}, {bs['ci_high']:+.3f}] "
                     f"| {'Có' if bs['significant'] else 'Không'} |")

    # Câu không dấu: lý do ban đầu để dùng trigram (chịu lỗi gõ/thiếu dấu)
    no_accent = [q for q in questions if "không dấu" in (q.get("note") or "") and q.get("relevant_chunk_ids")]
    if no_accent:
        ids = {q["id"] for q in no_accent}
        lines += ["", f"### Câu không dấu ({metric} từng câu)", "",
                  "| Câu | w=0.0 | w=" + str(CURRENT_W) + " | w=1.0 |", "|---|---|---|---|"]
        cols = [rag_eval.per_query([q for q in queries if q["id"] in ids],
                                   lambda c, w=w: rag_eval.hybrid_ranking(c, w), k) for w in (0.0, CURRENT_W, 1.0)]
        for i, q in enumerate(sorted(no_accent, key=lambda x: x["id"])):
            vals = [next(r[metric] for r in col if r["id"] == q["id"]) for col in cols]
            lines.append(f"| {q['id']}: {q['question']} | " + " | ".join(f"{v:.3f}" for v in vals) + " |")

    lines += [
        "",
        "![weight sweep](weight_sweep.svg)",
        "",
        "## Ngưỡng MIN_SCORE",
        "",
    ]
    if best_th:
        lines += [
            f"Điểm top-1 hybrid (w={CURRENT_W}) - câu có đoạn liên quan: "
            f"min {min(on):.3f} / TB {sum(on) / len(on):.3f}; câu không nên trích dẫn: "
            f"max {max(off):.3f} / TB {sum(off) / len(off):.3f}.",
            "",
            f"Ngưỡng tốt nhất theo F1: **{best_th['threshold']:.2f}** "
            f"(P={best_th['precision']:.3f}, R={best_th['recall']:.3f}, F1={best_th['f1']:.3f}); "
            f"ngưỡng hiện tại {CURRENT_MIN_SCORE}. Chi tiết: `min_score_sweep.csv`.",
        ]
    else:
        lines.append("Cần cả câu đúng chủ đề lẫn câu lạc đề (`off_topic: true`) để hiệu chỉnh ngưỡng.")
    (RESULTS / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"\nĐã ghi kết quả vào {RESULTS}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("candidates", help="Xuất ứng viên ra CSV để gán nhãn")
    p.add_argument("--questions", type=Path, default=QUESTIONS)
    p.add_argument("--csv", type=Path, default=LABELS_CSV)
    p.set_defaults(func=cmd_candidates)

    p = sub.add_parser("import-labels", help="Nạp cột relevant từ CSV vào bộ câu hỏi")
    p.add_argument("--questions", type=Path, default=QUESTIONS)
    p.add_argument("--csv", type=Path, default=LABELS_CSV)
    p.set_defaults(func=cmd_import_labels)

    p = sub.add_parser("sweep", help="Quét trọng số, so RRF, hiệu chỉnh MIN_SCORE")
    p.add_argument("--questions", type=Path, default=QUESTIONS)
    p.add_argument("--k", type=int, default=rag_eval.DEFAULT_K)
    p.add_argument("--metric", choices=["recall@k", "mrr", "ndcg@k"], default="ndcg@k")
    p.set_defaults(func=cmd_sweep)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

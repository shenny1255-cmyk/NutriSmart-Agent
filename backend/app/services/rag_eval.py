"""Chỉ số và thuật toán xếp hạng cho thực nghiệm trọng số Hybrid RAG (kế hoạch ĐATN v2, mục 2.4.1).

Trả lời câu hỏi của hội đồng "tại sao 0.7 / 0.3": quét w ∈ {0.0, 0.1, …, 1.0} trong
    score = w · cos(q, d) + (1 − w) · sim_trigram(q, d)
và so với baseline Pure Vector (w=1), Pure Trigram (w=0), RRF (k=60).

Toàn bộ là logic thuần trên dữ liệu đã lấy sẵn - script scripts/rag_weight_sweep.py lo
phần truy vấn Postgres/Ollama một lần, rồi tính lại xếp hạng cho mọi w ở đây (nhanh, lặp lại được).

Kiểu dữ liệu:
- candidates: dict[chunk_id, (cosine, trigram)] - điểm thành phần của mọi chunk ứng viên.
- query: {"id", "relevant": set[chunk_id], "candidates"} - relevant rỗng = chưa gán nhãn, bị bỏ qua.
"""
from __future__ import annotations

import math
from collections.abc import Callable, Iterable

DEFAULT_WEIGHTS = [round(i / 10, 1) for i in range(11)]
DEFAULT_K = 5
RRF_K = 60

Candidates = dict[int, tuple[float, float]]
Ranker = Callable[[Candidates], list[int]]


# ---------- Chỉ số ----------

def recall_at_k(ranked: list[int], relevant: set[int], k: int = DEFAULT_K) -> float:
    if not relevant:
        return 0.0
    return len(set(ranked[:k]) & relevant) / len(relevant)


def reciprocal_rank(ranked: list[int], relevant: set[int]) -> float:
    for i, cid in enumerate(ranked, start=1):
        if cid in relevant:
            return 1.0 / i
    return 0.0


def ndcg_at_k(ranked: list[int], relevant: set[int], k: int = DEFAULT_K) -> float:
    """nDCG nhị phân (liên quan = 1, không = 0)."""
    if not relevant:
        return 0.0
    dcg = sum(1.0 / math.log2(i + 1) for i, cid in enumerate(ranked[:k], start=1) if cid in relevant)
    idcg = sum(1.0 / math.log2(i + 1) for i in range(1, min(len(relevant), k) + 1))
    return dcg / idcg if idcg else 0.0


# ---------- Xếp hạng ----------

def hybrid_score(cosine: float, trigram: float, w: float) -> float:
    """Đúng công thức trong services/retrieval.py với W_VECTOR = w, W_TRIGRAM = 1 − w."""
    return w * cosine + (1.0 - w) * trigram


def _order(scores: dict[int, float]) -> list[int]:
    # Điểm giảm dần, hòa thì chunk_id tăng dần → kết quả lặp lại được
    return sorted(scores, key=lambda cid: (-scores[cid], cid))


def hybrid_ranking(candidates: Candidates, w: float) -> list[int]:
    return _order({cid: hybrid_score(c, t, w) for cid, (c, t) in candidates.items()})


def rrf_scores(candidates: Candidates, k: int = RRF_K) -> dict[int, float]:
    """Reciprocal Rank Fusion: score = Σ_i 1 / (k + rank_i), không cần chuẩn hóa điểm."""
    by_vec = _order({cid: c for cid, (c, _) in candidates.items()})
    by_trg = _order({cid: t for cid, (_, t) in candidates.items()})
    scores = {cid: 0.0 for cid in candidates}
    for ranking in (by_vec, by_trg):
        for rank, cid in enumerate(ranking, start=1):
            scores[cid] += 1.0 / (k + rank)
    return scores


def rrf_ranking(candidates: Candidates, k: int = RRF_K) -> list[int]:
    return _order(rrf_scores(candidates, k))


# ---------- Đánh giá ----------

def evaluate(queries: Iterable[dict], ranker: Ranker, k: int = DEFAULT_K) -> dict:
    """Trung bình Recall@k, MRR, nDCG@k trên các câu đã gán nhãn."""
    labeled = [q for q in queries if q.get("relevant")]
    if not labeled:
        return {"n": 0, "recall@k": 0.0, "mrr": 0.0, "ndcg@k": 0.0}
    rec = rr = nd = 0.0
    for q in labeled:
        ranked = ranker(q["candidates"])
        rec += recall_at_k(ranked, q["relevant"], k)
        rr += reciprocal_rank(ranked, q["relevant"])
        nd += ndcg_at_k(ranked, q["relevant"], k)
    n = len(labeled)
    return {"n": n, "recall@k": rec / n, "mrr": rr / n, "ndcg@k": nd / n}


def sweep_weights(queries: list[dict], weights: Iterable[float] = DEFAULT_WEIGHTS,
                  k: int = DEFAULT_K) -> list[dict]:
    return [
        {"w": w, **evaluate(queries, lambda c, w=w: hybrid_ranking(c, w), k)}
        for w in weights
    ]


def best_row(rows: list[dict], metric: str) -> dict:
    """Dòng có metric cao nhất (hòa → lấy dòng xuất hiện trước)."""
    return max(rows, key=lambda r: r[metric])


# ---------- Hiệu chỉnh ngưỡng MIN_SCORE ----------

def threshold_sweep(on_topic: list[float], off_topic: list[float],
                    thresholds: Iterable[float]) -> list[dict]:
    """Coi "câu đúng chủ đề" là lớp dương; dự đoán dương khi điểm top-1 ≥ ngưỡng.

    Precision thấp = để lọt câu lạc đề (trích dẫn sai); recall thấp = chặn nhầm câu đúng.
    """
    rows = []
    for t in thresholds:
        tp = sum(s >= t for s in on_topic)
        fn = len(on_topic) - tp
        fp = sum(s >= t for s in off_topic)
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
        rows.append({"threshold": t, "precision": precision, "recall": recall, "f1": f1,
                     "tp": tp, "fp": fp, "fn": fn})
    return rows


def best_threshold(rows: list[dict]) -> dict:
    """Ngưỡng F1 cao nhất; nhiều ngưỡng hòa → lấy trung vị (dưới) của khoảng hòa,
    để ngưỡng không nằm sát mép nhóm lạc đề hay nhóm đúng chủ đề."""
    top = max(r["f1"] for r in rows)
    ties = sorted((r for r in rows if r["f1"] == top), key=lambda r: r["threshold"])
    return ties[(len(ties) - 1) // 2]


def split_for_threshold(queries: list[dict]) -> tuple[list[dict], list[dict]]:
    """Chia câu hỏi cho bài toán ngưỡng MIN_SCORE.

    Dương: có ít nhất một đoạn liên quan → nên trích dẫn.
    Âm: câu lạc đề, hoặc đã gán nhãn mà kho không có đoạn nào trả lời → trích dẫn gì cũng sai.
    Câu chưa gán nhãn bị bỏ qua.
    """
    pos = [q for q in queries if q.get("relevant")]
    neg = [q for q in queries if not q.get("relevant") and (q.get("off_topic") or q.get("labeled"))]
    return pos, neg


def per_query(queries: Iterable[dict], ranker: Ranker, k: int = DEFAULT_K) -> list[dict]:
    """Điểm từng câu (chỉ câu có đoạn liên quan) - dùng cho kiểm định và phân tích lỗi."""
    out = []
    for q in queries:
        if not q.get("relevant"):
            continue
        ranked = ranker(q["candidates"])
        out.append({"id": q["id"],
                    "recall@k": recall_at_k(ranked, q["relevant"], k),
                    "mrr": reciprocal_rank(ranked, q["relevant"]),
                    "ndcg@k": ndcg_at_k(ranked, q["relevant"], k)})
    return out


def paired_bootstrap(a: list[float], b: list[float], n_resamples: int = 10000,
                     seed: int = 42, alpha: float = 0.05) -> dict:
    """Paired bootstrap cho hiệu trung bình (a - b) trên cùng bộ câu hỏi.

    significant = khoảng tin cậy (1 - alpha) không chứa 0.
    """
    import random
    assert len(a) == len(b) and a, "hai dãy phải cùng độ dài, khác rỗng"
    diffs = [x - y for x, y in zip(a, b)]
    n = len(diffs)
    rng = random.Random(seed)
    means = sorted(sum(diffs[rng.randrange(n)] for _ in range(n)) / n for _ in range(n_resamples))
    lo = means[int(alpha / 2 * n_resamples)]
    hi = means[min(n_resamples - 1, int((1 - alpha / 2) * n_resamples))]
    mean = sum(diffs) / n
    return {"mean_diff": round(mean, 10), "ci_low": round(lo, 10), "ci_high": round(hi, 10),
            "significant": not (lo <= 0 <= hi)}

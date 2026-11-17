"""Test chỉ số & thuật toán xếp hạng cho thực nghiệm trọng số Hybrid RAG (kế hoạch v2, mục 2.4.1).

Logic thuần - không cần Postgres/Ollama. Script chạy thật: scripts/rag_weight_sweep.py
"""
import math

import pytest

from app.services import rag_eval as re_


# ---------- Chỉ số truy hồi ----------

def test_recall_at_k():
    assert re_.recall_at_k([1, 2, 3, 4, 5, 6], {2, 6}, k=5) == 0.5
    assert re_.recall_at_k([1, 2], {1, 2}, k=5) == 1.0
    assert re_.recall_at_k([], {1}, k=5) == 0.0


def test_reciprocal_rank():
    assert re_.reciprocal_rank([9, 8, 3], {3}) == pytest.approx(1 / 3)
    assert re_.reciprocal_rank([3, 8], {3, 8}) == 1.0
    assert re_.reciprocal_rank([1, 2], {7}) == 0.0


def test_ndcg_at_k_nhi_phan():
    # Liên quan ở vị trí 1 và 3, có 2 đoạn liên quan
    dcg = 1 / math.log2(2) + 1 / math.log2(4)
    idcg = 1 / math.log2(2) + 1 / math.log2(3)
    assert re_.ndcg_at_k([5, 1, 6, 2], {5, 6}, k=5) == pytest.approx(dcg / idcg)
    assert re_.ndcg_at_k([5, 6], {5, 6}, k=5) == pytest.approx(1.0)
    assert re_.ndcg_at_k([1, 2], {9}, k=5) == 0.0


# ---------- Xếp hạng ----------

CANDS = {
    # chunk_id: (cosine, trigram)
    1: (0.90, 0.05),   # ngữ nghĩa rất gần, không trùng chữ
    2: (0.60, 0.80),   # trùng thuật ngữ mạnh
    3: (0.70, 0.30),
}


def test_hybrid_ranking_theo_trong_so():
    assert re_.hybrid_ranking(CANDS, w=1.0) == [1, 3, 2]        # thuần vector
    assert re_.hybrid_ranking(CANDS, w=0.0) == [2, 3, 1]        # thuần trigram
    # w=0.5: 1→0.475, 2→0.70, 3→0.50
    assert re_.hybrid_ranking(CANDS, w=0.5) == [2, 3, 1]


def test_hybrid_score_dung_cong_thuc_trong_retrieval():
    assert re_.hybrid_score(0.8, 0.4, w=0.7) == pytest.approx(0.7 * 0.8 + 0.3 * 0.4)


def test_rrf_scores_dung_cong_thuc():
    # Hạng vector: 1,3,2 ; hạng trigram: 2,3,1 → score = Σ 1/(k + rank)
    s = re_.rrf_scores(CANDS, k=60)
    assert s[1] == pytest.approx(1 / 61 + 1 / 63)
    assert s[2] == pytest.approx(1 / 63 + 1 / 61)
    assert s[3] == pytest.approx(2 / 62)
    # 1 và 2 hòa điểm → phá hòa theo chunk_id cho kết quả lặp lại được
    assert re_.rrf_ranking(CANDS, k=60) == [1, 2, 3]


# ---------- Đánh giá & quét trọng số ----------

QUERIES = [
    {"id": "q1", "relevant": {1}, "candidates": CANDS},
    {"id": "q2", "relevant": {2}, "candidates": CANDS},
    {"id": "q3", "relevant": set(), "candidates": CANDS},   # chưa gán nhãn → bỏ qua
]


def test_evaluate_trung_binh_tren_cau_da_gan_nhan():
    m = re_.evaluate(QUERIES, lambda c: re_.hybrid_ranking(c, w=1.0), k=1)
    assert m["n"] == 2
    assert m["recall@k"] == 0.5        # q1 đúng ở top-1, q2 sai
    assert m["mrr"] == pytest.approx((1 + 1 / 3) / 2)


def test_sweep_weights_tra_ve_moi_w_va_chon_tot_nhat():
    rows = re_.sweep_weights(QUERIES, weights=[0.0, 0.5, 1.0], k=1)
    assert [r["w"] for r in rows] == [0.0, 0.5, 1.0]
    best = re_.best_row(rows, metric="mrr")
    assert best["w"] in (0.0, 0.5, 1.0)
    assert all({"recall@k", "mrr", "ndcg@k", "n"} <= set(r) for r in rows)


def test_weight_grid_mac_dinh_0_den_1_buoc_0_1():
    assert re_.DEFAULT_WEIGHTS[0] == 0.0
    assert re_.DEFAULT_WEIGHTS[-1] == 1.0
    assert len(re_.DEFAULT_WEIGHTS) == 11


# ---------- Hiệu chỉnh ngưỡng MIN_SCORE ----------

def test_threshold_sweep_chon_nguong_theo_f1():
    on_topic = [0.56, 0.60, 0.48, 0.52]    # điểm top-1 của câu đúng chủ đề
    off_topic = [0.28, 0.31, 0.25]         # câu lạc đề
    rows = re_.threshold_sweep(on_topic, off_topic, thresholds=[0.30, 0.35, 0.50])
    by_t = {r["threshold"]: r for r in rows}
    assert by_t[0.35]["f1"] == 1.0          # tách sạch hai nhóm
    assert by_t[0.30]["precision"] < 1.0    # để lọt 1 câu lạc đề
    assert by_t[0.50]["recall"] < 1.0       # chặn nhầm 1 câu đúng chủ đề
    assert re_.best_row(rows, metric="f1")["threshold"] == 0.35


def test_best_threshold_lay_giua_khoang_hoa_de_co_bien_an_toan():
    rows = re_.threshold_sweep([0.56, 0.60], [0.28, 0.31],
                               thresholds=[0.30, 0.32, 0.40, 0.50, 0.56, 0.58])
    # F1 = 1 với mọi ngưỡng trong (0.31, 0.56] → chọn giữa khoảng thay vì sát mép
    assert re_.best_threshold(rows)["threshold"] == 0.40


def test_phan_lop_cau_hoi_cho_hieu_chinh_nguong():
    # Dương: có đoạn liên quan. Âm: lạc đề, hoặc đã gán nhãn mà kho không có đoạn nào trả lời.
    # Chưa gán nhãn → bỏ qua (không biết thuộc lớp nào).
    qs = [
        {"id": "a", "relevant": {1}, "labeled": True},
        {"id": "b", "relevant": set(), "labeled": True},
        {"id": "c", "relevant": set(), "off_topic": True},
        {"id": "d", "relevant": set()},
    ]
    pos, neg = re_.split_for_threshold(qs)
    assert [q["id"] for q in pos] == ["a"]
    assert [q["id"] for q in neg] == ["b", "c"]


def test_per_query_tra_diem_tung_cau():
    rows = re_.per_query(QUERIES, lambda c: re_.hybrid_ranking(c, w=1.0), k=1)
    assert [r["id"] for r in rows] == ["q1", "q2"]          # bỏ câu chưa gán nhãn
    assert rows[0]["mrr"] == 1.0 and rows[1]["mrr"] == pytest.approx(1 / 3)


def test_paired_bootstrap_khoang_tin_cay():
    a = [0.5, 0.6, 0.7, 0.8] * 10
    same = re_.paired_bootstrap(a, a, n_resamples=500, seed=1)
    assert same["mean_diff"] == 0.0 and same["ci_low"] == 0.0 and same["ci_high"] == 0.0
    better = re_.paired_bootstrap([x + 0.1 for x in a], a, n_resamples=500, seed=1)
    assert better["mean_diff"] == pytest.approx(0.1)
    assert better["ci_low"] > 0                              # khác biệt rõ → CI không chứa 0
    assert better["significant"] is True

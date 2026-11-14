# Bộ đánh giá NutriSmart (kế hoạch ĐATN v2)

## Thực nghiệm trọng số Hybrid RAG — "tại sao 0.7 / 0.3?"

Công thức trong `app/services/retrieval.py`:

    score = w · cos(q, d) + (1 − w) · sim_trigram(q, d),   hiện tại w = 0.7, MIN_SCORE = 0.35

Thành phần thứ hai là **trigram similarity (pg_trgm)**, không phải BM25.

### Quy trình (chạy từ `backend/`, cần Postgres + Ollama `bge-m3`)

1. **Bổ sung câu hỏi** vào `rag_questions.json` (mục tiêu 50–100 câu, có cả câu lạc đề
   `"off_topic": true`). Câu hỏi nên bám nội dung kho tài liệu đã duyệt.
2. **Xuất ứng viên:**
   `PYTHONUTF8=1 ./.venv/Scripts/python.exe scripts/rag_weight_sweep.py candidates`
   → `rag_labels.csv` (mở bằng Excel). Mỗi câu có ứng viên gộp từ top của Pure Vector,
   Pure Trigram và Hybrid w hiện tại — để việc gán nhãn không thiên vị trọng số nào.
3. **Gán nhãn:** điền `1` vào cột `relevant` cho đoạn trả lời được (dù chỉ một phần) câu hỏi.
   Câu lạc đề để trống toàn bộ. Nên có 2 người gán độc lập một mẫu ngẫu nhiên để báo cáo
   độ đồng thuận; Expert duyệt mẫu.
4. **Nạp nhãn:** `... scripts/rag_weight_sweep.py import-labels`
5. **Quét:** `... scripts/rag_weight_sweep.py sweep [--metric ndcg@k|mrr|recall@k] [--k 5]`
   → `results/report.md`, `results/weight_sweep.csv`, `results/weight_sweep.svg`,
   `results/min_score_sweep.csv`.

### Đọc kết quả

- Bảng Recall@5 / MRR / nDCG@5 cho w = 0.0 … 1.0, kèm baseline Pure Vector (w=1),
  Pure Trigram (w=0) và RRF (k=60).
- Đỉnh quanh 0.7 → có bằng chứng giữ nguyên; nếu không → đổi `W_VECTOR`/`W_TRIGRAM`.
  Cả hai đều là kết quả có giá trị. Với cỡ mẫu nhỏ, chênh lệch vài phần trăm có thể chỉ là nhiễu.
- `MIN_SCORE`: chọn ngưỡng theo F1 giữa điểm top-1 của câu đúng chủ đề và câu lạc đề.

Logic chỉ số nằm ở `app/services/rag_eval.py` (có test trong `tests/test_rag_eval.py`).

## Warning Engine (guardrails)

Rule nằm ở `app/services/guardrails.py`; bộ test case bệnh lý & dị ứng (gồm dị ứng ẩn) ở
`tests/test_guardrails.py`. Các nguồn tham khảo trong rule cần đối chiếu bản gốc trước khi
trích dẫn trong khóa luận.

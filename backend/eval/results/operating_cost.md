# Bảng chi phí vận hành AI đám mây

- Đơn giá: https://ai.google.dev/gemini-api/docs/pricing (Paid tier, Standard, tra ngày 17/11/2026)
- Tỷ giá: 25.950 VND/USD (Vietcombank. giá bán ngày 17/11/2026)
- Token đo trên chính hệ thống, trừ dòng ghi "ước lượng". Tạo lại: `scripts/operating_cost.py`.

## 1. Chi phí mỗi request (gemini-3.5-flash-lite)

| Tác vụ | Token vào | Token ra | USD/request | VND/request | Cơ sở số liệu |
|---|---|---|---|---|---|
| Chat tư vấn (kèm RAG + lịch sử) | 1.514 | 374 | $0.00139 | 36 đ | đo thật: TB 7 lượt chat qua API (audit_logs), độ trễ trung vị ~2,9 s |
| Phân tích ảnh món ăn | 1.513 | 162 | $0.00086 | 22 đ | đo thật: 3 ảnh mẫu (usage_metadata); ảnh ~1.090 token + prompt 424 token, ~2,3 s |
| Sinh lộ trình 7 ngày (JSON) | 601 | 1.202 | $0.00319 | 83 đ | đo thật: scripts/llm_benchmark.py (eval/results/llm_benchmark.md), ~4,9 s |
| Nhận xét check-in / đánh giá chu kỳ | 600 | 200 | $0.00068 | 18 đ | ước lượng (chưa đo): prompt ngắn, giới hạn 180-220 token ra |

Token ra đắt hơn token vào 8 lần nên câu trả lời dài (chat, lộ trình) chiếm phần lớn chi phí.

## 2. Chi phí theo tháng

Giả định một người dùng hoạt động/tháng:

- Chat tư vấn (kèm RAG + lịch sử): 90 lần
- Phân tích ảnh món ăn: 60 lần
- Sinh lộ trình 7 ngày (JSON): 5 lần
- Nhận xét check-in / đánh giá chu kỳ: 9 lần

→ **$0.199 ≈ 5.154 đ / người dùng / tháng**

| Người dùng hoạt động | gemini-3.5-flash-lite | gemini-3.1-flash-lite | gemini-2.5-flash-lite |
|---|---|---|---|
| 100 | $19.86 (515.389 đ) | $13.56 (352.002 đ) | $4.40 (114.233 đ) |
| 1.000 | $198.61 (5.153.891 đ) | $135.65 (3.520.020 đ) | $44.02 (1.142.332 đ) |
| 10.000 | $1,986.09 (51.538.906 đ) | $1,356.46 (35.200.202 đ) | $440.21 (11.423.320 đ) |

Cơ cấu chi phí mỗi người dùng/tháng (model mặc định):

| Tác vụ | USD/tháng | Tỷ trọng |
|---|---|---|
| Chat tư vấn (kèm RAG + lịch sử) | $0.1250 | 63% |
| Phân tích ảnh món ăn | $0.0515 | 26% |
| Sinh lộ trình 7 ngày (JSON) | $0.0159 | 8% |
| Nhận xét check-in / đánh giá chu kỳ | $0.0061 | 3% |

## 3. Ghi chú để trình bày trung thực

- **Gói miễn phí** (Free tier) không tốn tiền nhưng Google ghi rõ nội dung gửi lên *được dùng để cải thiện sản phẩm của Google* và giới hạn số request. Chỉ phù hợp cho demo với dữ liệu đã ẩn danh. Khi có người dùng thật nên dùng gói trả phí (nội dung *không* dùng để cải thiện sản phẩm).
- **Chi phí cố định không nằm trong bảng:** máy chủ backend + PostgreSQL, và Ollama trên máy chủ vẫn cần cho embedding `bge-m3` (RAG) và làm phương án dự phòng/chế độ "chỉ AI nội bộ". Không cần Ollama ở máy người dùng.
- **So với chạy hoàn toàn nội bộ:** Ollama (gemma3:1b) trên CPU máy phát triển mất ~17 s/câu chat và ~90 s/lộ trình (eval/results/llm_benchmark.md), không phục vụ được nhiều người cùng lúc; muốn nhanh cần GPU thuê theo giờ - chi phí cố định, chưa khảo sát báo giá trong đồ án này.
- **Cách giảm chi phí có sẵn trong bảng giá:** Batch API giảm 50% - hợp với job nền (nhận xét check-in, đánh giá chu kỳ) vì không cần trả lời ngay; giới hạn độ dài câu trả lời (`LLM_MAX_OUTPUT_TOKENS`).
- Tần suất dùng là giả định; đổi `USAGE_PER_USER_MONTH` trong script rồi chạy lại để có bảng mới.

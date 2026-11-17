# Đo độ trễ và token theo nhà cung cấp AI

- Thời điểm đo: 2026-11-17 13:25 · máy chạy backend: máy phát triển của nhóm
- `chat`: câu hỏi tư vấn ngắn kèm hồ sơ · `plan`: sinh lộ trình 7 ngày JSON theo schema (đã kiểm tra hợp lệ)
- Ollama chạy trên chính máy phát triển (CPU), chưa phải GPU server; Gemini gọi qua Internet.

| Provider | Tác vụ | Model | Thành công | p50 (s) | p95 (s) | Max (s) | Token vào TB | Token ra TB |
|---|---|---|---|---|---|---|---|---|
| ollama | chat | gemma3:1b | 5/5 | 17.44 | 21.41 | 22.06 | - | - |
| ollama | plan | gemma3:1b | 1/1 | 89.98 | 89.98 | 89.98 | - | - |
| gemini | chat | gemini-3.5-flash-lite | 5/5 | 2.30 | 3.01 | 3.03 | 84 | 104 |
| gemini | plan | gemini-3.5-flash-lite | 1/1 | 4.85 | 4.85 | 4.85 | 601 | 1202 |

Số token dùng để điền bảng chi phí vận hành (mục 2.2 kế hoạch): chi phí/request = token vào × đơn giá vào + token ra × đơn giá ra (tra bảng giá hiện hành).

# Kết quả đánh giá Warning Engine

- Thời điểm chạy: 2026-11-17 14:15
- Bảng món → nguyên liệu: 76 món (`data/dish_ingredients.json`, chưa duyệt)
- Baseline "không có guardrail": recall = 0 cho mọi loại cảnh báo.

## Bộ dev

Bộ dev (73 case từ GĐ2). 13 ca bỏ sót đã được công bố trong báo cáo GĐ2 trước khi soạn bảng món, nên kết quả trên bộ này **bị lạc quan**, chỉ dùng để kiểm tra hồi quy.

### dev - không có bảng món (73 case, `eval/guardrail_cases.json`)

| Loại | TP | FP | FN | TN | Precision | Recall | Tỷ lệ báo động giả |
|---|---|---|---|---|---|---|---|
| Dị ứng | 27 | 0 | 11 | 35 | 1.000 | 0.711 | 0.000 |
| Bệnh nền | 13 | 0 | 2 | 58 | 1.000 | 0.867 | 0.000 |

### dev - có bảng món (73 case, `eval/guardrail_cases.json`)

| Loại | TP | FP | FN | TN | Precision | Recall | Tỷ lệ báo động giả |
|---|---|---|---|---|---|---|---|
| Dị ứng | 38 | 0 | 0 | 35 | 1.000 | 1.000 | 0.000 |
| Bệnh nền | 15 | 0 | 0 | 58 | 1.000 | 1.000 | 0.000 |

Bỏ sót: 0

Báo động giả: 0

## Bộ holdout

Bộ holdout (40 case, 1/3 là ca âm) viết và chốt trước khi soạn bảng món. Lưu ý trung thực: cùng một người viết holdout rồi soạn bảng món ngay sau đó, nên vẫn **chưa phải đánh giá mù**. Số liệu công bố cuối cùng cần một bộ do thành viên khác viết mà không xem bảng món.

### holdout - không có bảng món (40 case, `eval/guardrail_cases_holdout.json`)

| Loại | TP | FP | FN | TN | Precision | Recall | Tỷ lệ báo động giả |
|---|---|---|---|---|---|---|---|
| Dị ứng | 0 | 0 | 18 | 22 | 0.000 | 0.000 | 0.000 |
| Bệnh nền | 0 | 0 | 9 | 31 | 0.000 | 0.000 | 0.000 |

### holdout - có bảng món (40 case, `eval/guardrail_cases_holdout.json`)

| Loại | TP | FP | FN | TN | Precision | Recall | Tỷ lệ báo động giả |
|---|---|---|---|---|---|---|---|
| Dị ứng | 18 | 0 | 0 | 22 | 1.000 | 1.000 | 0.000 |
| Bệnh nền | 9 | 0 | 0 | 31 | 1.000 | 1.000 | 0.000 |

Bỏ sót: 0

Báo động giả: 0


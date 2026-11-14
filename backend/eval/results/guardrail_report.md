# Kết quả đánh giá Warning Engine

- Thời điểm chạy: 2026-11-14 11:30
- Số test case: **73** (`eval/guardrail_cases.json`)
- Baseline "không có guardrail": recall = 0 cho mọi loại cảnh báo.

| Loại | TP | FP | FN | TN | Precision | Recall | Tỷ lệ báo động giả |
|---|---|---|---|---|---|---|---|
| Dị ứng | 27 | 0 | 11 | 35 | 1.000 | 0.711 | 0.000 |
| Bệnh nền | 13 | 0 | 2 | 58 | 1.000 | 0.867 | 0.000 |

## Bỏ sót (13)
Phần lớn là **dị ứng ẩn trong tên món** — từ điển chỉ thấy chữ, không biết công thức. Hướng khắc phục: bảng món → nguyên liệu từ dữ liệu Viện Dinh dưỡng (GĐ1).

| ID | Món | Hồ sơ | Kỳ vọng | Hệ thống bật | Ghi chú |
|---|---|---|---|---|---|
| a05 | Bún bò Huế | Hải sản có vỏ | ALLERGEN | — | nước dùng có mắm ruốc — dị ứng ẩn |
| a06 | Bánh xèo | Hải sản có vỏ | ALLERGEN | — | nhân tôm |
| a07 | Chả giò | Hải sản có vỏ | ALLERGEN | — | nhân thường có tôm/cua |
| a08 | Cơm chiên Dương Châu | Hải sản có vỏ | ALLERGEN | — | có tôm |
| b03 | Bún chả Hà Nội | Cá | ALLERGEN | — | nước chấm pha nước mắm — dị ứng ẩn |
| c03 | Gỏi gà bắp cải | Đậu phộng | ALLERGEN | — | thường rắc lạc rang — dị ứng ẩn |
| c04 | Bánh đa kê | Đậu phộng | ALLERGEN | — | có lạc |
| d06 | Sinh tố bơ | Sữa bò | ALLERGEN | — | thường xay cùng sữa đặc/sữa tươi — dị ứng ẩn |
| e06 | Bò lúc lắc | Gluten | ALLERGEN | — | ướp xì dầu (có lúa mì) — dị ứng ẩn |
| f03 | Cơm tấm sườn bì chả | Trứng | ALLERGEN | — | chả trứng hấp — dị ứng ẩn |
| h04 | Phở tái lăn | Thịt bò | ALLERGEN | — | phở tái = thịt bò — dị ứng ẩn |
| m04 | Bánh bò nướng | Đái tháo đường típ 2 | CONDITION | — | bánh ngọt nhiều đường — tên không lộ |
| n03 | Thịt kho tàu | Tăng huyết áp | CONDITION | — | kho mặn nhiều nước mắm — tên không lộ |

## Báo động giả (0)

| ID | Món | Hồ sơ | Kỳ vọng | Hệ thống bật | Ghi chú |
|---|---|---|---|---|---|

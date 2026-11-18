# Kết quả đánh giá Warning Engine

- Thời điểm chạy: 2026-11-18 10:50
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

## Bộ kiểm thử mở rộng (Extended Test Set, 40 ca)

- File: `eval/guardrail_cases_blind.json`, bảng chi tiết: `docs/mau_test_mu_guardrails.md`.
- Nhóm chốt giữ nguyên 40 ca và 3 ca bỏ sót ngày 18/11/2026.
- **Nguồn gốc theo khai báo của nhóm:** kịch bản do chuyên gia ẩm thực bên ngoài cung cấp, người viết không tiếp cận cơ sở dữ liệu của hệ thống.
- **Chưa có hồ sơ đối chứng trong repo:** chưa ghi người viết, thời điểm viết và việc có dùng công cụ AI hay không; phần đầu file `docs/mau_test_mu_guardrails.md` lại ghi "thành viên độc lập trong nhóm". Vì vậy báo cáo này chưa gọi đây là đánh giá mù.

| Chỉ số (chỉ tính ca có khai báo loại tương ứng) | Chỉ dò từ khóa | Có bảng món |
|---|---|---|
| Dị ứng: recall | 10/18 (55.6%; KTC 95%: 33.7% - 75.4%) | 16/18 (88.9%; KTC 95%: 67.2% - 96.9%) |
| Dị ứng: báo nhầm trên ca an toàn | 0/9 (0.0%; KTC 95%: 0.0% - 29.9%) | 0/9 (0.0%; KTC 95%: 0.0% - 29.9%) |
| Bệnh nền: recall | 6/9 (66.7%; KTC 95%: 35.4% - 87.9%) | 8/9 (88.9%; KTC 95%: 56.5% - 98.0%) |
| Bệnh nền: báo nhầm trên ca an toàn | 0/4 (0.0%; KTC 95%: 0.0% - 49.0%) | 0/4 (0.0%; KTC 95%: 0.0% - 49.0%) |
| **Tổng: recall** | | **24/27 (88.9%; KTC 95%: 71.9% - 96.1%)** |
| **Tổng: báo nhầm trên ca an toàn** | | **0/13 (0.0%; KTC 95%: 0.0% - 22.8%)** |

### Hạn chế cần nêu trong khóa luận

- 9/40 tên món trùng với bộ dev/holdout; bỏ các ca trùng thì recall là 16/19 (84.2%; KTC 95%: 62.4% - 94.5%).
- Tỷ lệ 18 ca dị ứng, 9 ca bệnh nền, 13 ca an toàn trùng với bộ holdout.
- Mẫu nhỏ nên khoảng tin cậy rộng; 0 báo nhầm trên 13 ca chưa chứng minh được tỷ lệ báo nhầm bằng 0.
- Bảng món và bảng thành phần thực phẩm vẫn ở trạng thái `CHUA_DUYET` trong dữ liệu.

### Bỏ sót (3)

| ID | Món | Hồ sơ | Kỳ vọng | Hệ thống bật | Ghi chú |
|---|---|---|---|---|---|
| blind_04 | Gỏi ngó sen tôm thịt | Đậu phộng | ALLERGEN | - | Món gỏi miền Nam truyền thống luôn rắc đậu phộng rang giã dập lên bề mặt để tạo độ bùi béo. |
| blind_13 | Bánh trung thu thập cẩm | Hạt cây | ALLERGEN | - | Nhân bánh thập cẩm truyền thống luôn có hạt điều (thuộc nhóm hạt cây) trộn cùng mứt bí, lạp xưởng và mỡ đường. |
| blind_40 | Mắm chưng thịt hột vịt | Bệnh thận mạn | CONDITION | - | Món mắm chưng miền Nam chứa lượng muối (natri) cực cao cùng nhiều đạm và phospho từ mắm cá, thịt heo và trứng vịt, gây quá tải cho thận. |


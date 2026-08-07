# Tổng kết triển khai Check-in tiến độ 14 ngày

## 1. Mục tiêu đã hoàn thành

Tính năng tạo một chu kỳ theo dõi tiến độ thống nhất sau mỗi 14 ngày. Người dùng báo cáo số liệu thực tế, backend đánh giá bằng quy tắc cố định và chỉ dùng Ollama để viết nhận xét dễ hiểu.

Các kết quả chính:

- Thay luồng đánh giá 7 ngày cũ bằng check-in 14 ngày.
- Mỗi người dùng chỉ có một chuỗi coaching và một kỳ check-in đang mở.
- Lưu snapshot đầu kỳ để kết quả không thay đổi theo hồ sơ về sau.
- Đánh giá tiến độ không phụ thuộc vào tốc độ Ollama.
- Không tự điều chỉnh kcal nếu dữ liệu thiếu, tuân thủ thấp hoặc có cảnh báo an toàn.
- Chỉ tạo phiên bản kế hoạch mới sau khi người dùng xác nhận áp dụng điều chỉnh.
- Có lịch sử check-in, thông báo và kỳ tiếp theo.

## 2. Luồng hoàn chỉnh

```text
Người dùng tạo lộ trình
        ↓
Backend đóng chuỗi coaching và kỳ OPEN cũ
        ↓
Tạo chuỗi coaching mới + kỳ check-in số 1
        ↓
Chụp snapshot cân nặng, mục tiêu, kcal và vận động đầu kỳ
        ↓
Người dùng thực hiện lộ trình và ghi nhật ký trong 14 ngày
        ↓
Hệ thống gửi thông báo sắp đến hạn/đến hạn/quá hạn
        ↓
Ngày thứ 14: form check-in được mở
        ↓
Người dùng nhập số liệu và mức thực hiện lộ trình
        ↓
Backend khóa bản ghi, kiểm tra quyền, trạng thái và dữ liệu
        ↓
Tổng hợp nhật ký + đánh giá theo quy tắc cố định
        ↓
Trả kết quả ngay, đồng thời đưa feedback AI vào hàng chờ
        ↓
Người dùng sửa số liệu hoặc xác nhận quyết định
        ↓
CONTINUE: giữ plan hiện tại và tạo kỳ tiếp theo
APPLY_ADJUSTMENT: tạo plan version mới rồi tạo kỳ tiếp theo
```

## 3. Chu kỳ và trạng thái

Một kỳ gồm:

- Ngày bắt đầu: `D`.
- Ghi nhận dữ liệu: `D` đến `D + 13`.
- Mở form: `D + 14`.
- Cho phép nhập muộn đến hết `D + 17`.

Trạng thái lưu trong database:

- `OPEN`: chưa gửi báo cáo.
- `COMPLETED`: đã gửi và đánh giá xong.
- `MISSED`: hết thời gian gia hạn.
- `CANCELLED`: bị hủy do tạo hoặc thay kế hoạch khác.

Trạng thái hiển thị được suy ra từ ngày:

- `UPCOMING`: chưa đến ngày gửi.
- `DUE`: đã có thể gửi và còn trong hạn.
- `OVERDUE`: đã quá hạn, chờ reconcile thành `MISSED`.

## 4. Dữ liệu đầu kỳ

Khi tạo kỳ, hệ thống lưu snapshot:

- Cân nặng đầu kỳ.
- Mục tiêu sức khỏe.
- Mức kcal của plan.
- Mức vận động mục tiêu.
- Khoảng cân nặng kỳ vọng.
- Version của quy tắc dự đoán.

Baseline lấy từ `body_metrics_history` mới nhất; nếu chưa có thì dùng cân nặng trong hồ sơ sức khỏe.

## 5. Form check-in

Người dùng nhập:

- Cân nặng hiện tại: `20–300 kg`.
- Vòng eo tùy chọn: `30–250 cm`.
- Mức vận động thực tế: `1–5`.
- Mức năng lượng: `1–5`.
- Mức đói: `1–5`.
- Chất lượng giấc ngủ: `1–5`.
- Ghi chú tối đa 1.000 ký tự.

Mức thực hiện lộ trình được trình bày thành năm lựa chọn:

- `0–20%`: Hầu như không thực hiện.
- `21–40%`: Thực hiện ít.
- `41–60%`: Thực hiện khoảng một nửa.
- `61–80%`: Thực hiện phần lớn.
- `81–100%`: Gần như thực hiện đầy đủ.

Form được lưu nháp trong `sessionStorage`, nên chuyển trang rồi quay lại không mất dữ liệu.

## 6. Kiểm tra dữ liệu phi logic

Frontend và backend đều kiểm tra dữ liệu.

- Từ chối cân nặng ngoài `20–300 kg`.
- Từ chối vòng eo ngoài `30–250 cm`.
- Từ chối cân nặng thay đổi quá 20% so với đầu kỳ.
- Hiển thị lỗi đỏ ngay tại trường nhập.
- Không thể bỏ qua validation frontend bằng cách gọi API trực tiếp.

Biến động đáng kể nhưng chưa vượt mức chặn vẫn được lưu và chuyển sang cảnh báo an toàn.

## 7. Quy tắc đánh giá

Backend tính các kết quả sau:

### Chất lượng dữ liệu

- `SUFFICIENT`: đủ dữ liệu cân nặng và nhật ký.
- `PARTIAL`: có cân nặng nhưng thiếu nhật ký.
- `INSUFFICIENT`: gần như không có dữ liệu theo dõi.

### Mức tuân thủ

- `HIGH`: từ 80%.
- `MEDIUM`: 50–79%.
- `LOW`: dưới 50%.

### Kết quả cân nặng

- `WITHIN_EXPECTED_RANGE`: trong khoảng kỳ vọng.
- `BELOW_EXPECTED_RANGE`: thấp hơn khoảng kỳ vọng.
- `ABOVE_EXPECTED_RANGE`: cao hơn khoảng kỳ vọng.
- `NOT_EVALUATED`: chưa đủ điều kiện kết luận.

### Khuyến nghị

- `CONTINUE_AND_TRACK`: tiếp tục và ghi nhật ký.
- `IMPROVE_ADHERENCE`: cải thiện mức thực hiện.
- `CONTINUE`: tiếp tục lộ trình.
- `CONTINUE_AND_MONITOR`: theo dõi thêm một kỳ.
- `ADJUST_PLAN`: có thể điều chỉnh lộ trình.
- `NEEDS_REVIEW`: phát hiện thay đổi bất thường.

Chỉ đề xuất điều chỉnh kcal khi:

- Dữ liệu đủ.
- Mức tuân thủ cao.
- Không có cảnh báo an toàn.
- Sai lệch bất lợi xảy ra hai kỳ liên tiếp.

## 8. Cảnh báo an toàn

Các cờ hiện có:

- Cân nặng thay đổi nhanh.
- Năng lượng quá thấp.
- Đói cao.
- Giấc ngủ kém.
- Mục tiêu hoặc tình trạng cần thận trọng.

Khi có cảnh báo nghiêm trọng:

- Không hiển thị nút tự động điều chỉnh kcal.
- Hiển thị **Phát hiện thay đổi bất thường**.
- Hướng dẫn người dùng kiểm tra lại số liệu và trao đổi với chuyên gia y tế nếu số liệu chính xác.

Hệ thống không tuyên bố đã tự động gửi báo cáo cho một chuyên gia.

## 9. Sửa số liệu báo cáo

Sau khi gửi nhưng trước khi chọn quyết định, người dùng có thể bấm:

**Sửa số liệu báo cáo**

Luồng sửa:

- Backend mở lại check-in.
- Form điền sẵn dữ liệu đã nhập.
- Feedback AI cũ bị hủy.
- Người dùng sửa và gửi lại.
- Backend tính lại toàn bộ kết quả và tạo feedback mới.

Không cho sửa sau khi đã chốt quyết định.

## 10. Quyết định sau check-in

### Tiếp tục lộ trình

- Ghi `decision=CONTINUE`.
- Giữ plan version hiện tại.
- Tạo đúng một kỳ check-in tiếp theo.

### Áp dụng điều chỉnh

Chỉ xuất hiện khi recommendation là `ADJUST_PLAN`.

- Ghi `decision=APPLY_ADJUSTMENT`.
- Tạo plan version mới.
- Liên kết với plan cũ bằng `parent_plan_id`.
- Tạo kỳ tiếp theo dùng plan mới.

Request lặp không tạo thêm plan version hoặc kỳ check-in.

## 11. Feedback Ollama

Ollama chỉ diễn giải kết quả đã được backend quyết định.

- Submit check-in không chờ Ollama.
- Kết quả quy tắc được trả ngay.
- Feedback được xử lý nền với trạng thái `PENDING`.
- Thành công chuyển sang `COMPLETED`.
- Thất bại dùng nội dung fallback an toàn và chuyển sang `FAILED`.
- Frontend polling nhẹ khi feedback đang được tạo.
- Nếu người dùng mở lại báo cáo trong lúc Ollama chạy, feedback cũ không được ghi đè vào báo cáo mới.

## 12. Thông báo

Hệ thống tạo thông báo:

- Còn hai ngày đến check-in.
- Đã đến ngày check-in.
- Check-in đang trong thời gian gia hạn.

Notification có `dedupe_key`, nên scheduler chạy lại không tạo thông báo trùng. Người dùng xem và đánh dấu đã đọc từ biểu tượng chuông ở dashboard.

## 13. Chế độ thử nghiệm

Admin trong môi trường không phải production thấy nút:

**Thử nghiệm · Mở check-in ngay**

Nút cho phép kiểm tra form mà không chờ 14 ngày:

- Backend xử lý việc mô phỏng.
- Không thay đổi ngày hệ thống của máy.
- User thường không gọi được endpoint.
- Production trả `404`.
- Không mô phỏng lại kỳ đã đến hạn hoặc đã xử lý.

## 14. API đã triển khai

```http
GET  /api/v1/plans/active/checkin
GET  /api/v1/plans/checkins/history?limit=10
POST /api/v1/plans/checkins/{id}/submit
POST /api/v1/plans/checkins/{id}/reopen
POST /api/v1/plans/checkins/{id}/decision
POST /api/v1/plans/checkins/current/simulate-due

GET  /api/v1/notifications
PUT  /api/v1/notifications/{id}/read
```

Luồng đánh giá 7 ngày cũ đã bị vô hiệu hóa và trả `410 Gone`.

## 15. Database đã triển khai

Migration: `db/migrations/19_periodic_checkins.sql`

Các thành phần chính:

- `plan_checkin_series`
- `plan_checkins`
- `nutrition_plans.parent_plan_id`
- `notifications.dedupe_key`
- Unique index cho một series ACTIVE.
- Unique index cho một check-in OPEN.
- Unique index chống notification trùng.
- Quan hệ giữa plan cũ và plan điều chỉnh.

## 16. Các file chính

Backend:

- `backend/app/services/plan_checkin.py`
- `backend/app/routers/plans.py`
- `backend/app/routers/notifications.py`
- `backend/app/services/plan_generator.py`
- `backend/app/models.py`
- `backend/app/schemas.py`
- `backend/app/main.py`
- `backend/app/config.py`

Frontend:

- `frontend/src/pages/Plan.jsx`
- `frontend/src/pages/dashboard.jsx`
- `frontend/src/lib/api.js`

Database và test:

- `db/migrations/19_periodic_checkins.sql`
- `backend/tests/test_plan_checkin.py`

## 17. Kết quả kiểm thử

- Test backend check-in: `35 passed`.
- Đã kiểm tra quyền sở hữu check-in.
- Đã kiểm tra submit và decision idempotent.
- Đã kiểm tra không tạo trùng body metric.
- Đã kiểm tra adjustment chỉ tạo một plan version.
- Đã kiểm tra mô phỏng nhiều kỳ vẫn lấy đúng kỳ mới nhất.
- Đã kiểm tra cân nặng thay đổi quá 20% bị từ chối.
- Frontend production build thành công.
- Frontend lint không có error; còn một số warning cũ ngoài phạm vi tính năng.

## 18. Tài liệu liên quan

- `plan.md`: đặc tả và kế hoạch triển khai ban đầu.
- `plan_completed.md`: tài liệu tổng kết tính năng đã hoàn thành.
- `plan_followup.md`: các lỗ hổng và hướng phát triển tiếp theo.

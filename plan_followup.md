# Rà soát sau triển khai Check-in 14 ngày

## Trạng thái

Luồng chính trong `plan.md` đã hoàn thành và đủ dùng để demo:

- Tạo chu kỳ check-in 14 ngày.
- Mở form đúng hạn và có chế độ mô phỏng dành cho admin.
- Đánh giá bằng quy tắc backend, không phụ thuộc Ollama.
- Cảnh báo thay đổi cân nặng bất thường.
- Cho phép tiếp tục hoặc áp dụng điều chỉnh khi đủ điều kiện.
- Lưu lịch sử, thông báo và tạo kỳ tiếp theo.

Trước khi đưa lên production nên xử lý các mục dưới đây.

## P0 — Cần sửa trước khi production

### 1. Khôi phục cân nặng khi mở lại báo cáo

Hiện tại submit check-in cập nhật ngay:

- `user.info.weight_kg`
- `body_metrics_history`

Nếu người dùng bấm **Sửa số liệu báo cáo** rồi rời trang mà không gửi lại, cân nặng sai vẫn còn trong hồ sơ và có thể trở thành baseline của kỳ sau.

Hướng xử lý:

- Ưu tiên chỉ cập nhật cân nặng chính thức sau khi người dùng xác nhận quyết định; hoặc
- Khi mở lại báo cáo, khôi phục giá trị cân nặng và bản ghi lịch sử trước lần submit.

### 2. Thêm lịch sử chỉnh sửa check-in

Không nên sửa một báo cáo đã hoàn tất mà không lưu dấu vết.

Tạo audit/revision lưu:

- Check-in được sửa.
- Giá trị trước và sau.
- Người thực hiện.
- Thời điểm sửa.
- Lý do sửa nếu cần.

Không cho sửa sau khi đã áp dụng điều chỉnh kế hoạch.

### 3. Không sửa ngày nghiệp vụ khi mô phỏng

Nút demo hiện thay đổi trực tiếp `start_date`, `period_end`, `due_date` và `grace_until`. Mô phỏng nhiều kỳ có thể tạo các khoảng ngày trùng nhau.

Hướng xử lý:

- Thêm `simulated_today` hoặc cơ chế đồng hồ giả chỉ dùng trong development.
- Giữ nguyên toàn bộ ngày nghiệp vụ gốc.
- Dữ liệu mô phỏng phải được nhận diện hoặc có thể reset dễ dàng.

### 4. Khóa công cụ demo theo cấu hình an toàn

Dùng cờ riêng:

```env
ENABLE_DEMO_TOOLS=false
```

Yêu cầu:

- Mặc định là `false`.
- Chỉ bật rõ ràng ở máy local/demo.
- Endpoint vẫn yêu cầu quyền `ADMIN`.
- Production trả `404` kể cả khi client tự gọi endpoint.

### 5. Có cơ chế chạy migration cho database cũ

`docker-entrypoint-initdb.d` chỉ chạy khi PostgreSQL tạo volume mới. Máy đã có database sẽ không tự nhận migration 19.

Nên chọn một giải pháp:

- Dùng Alembic; hoặc
- Tạo migration runner có bảng ghi phiên bản; hoặc
- Chạy script migration bắt buộc trong quy trình deploy.

## P1 — Nên hoàn thiện sau P0

### 6. Đưa ngưỡng nghiệp vụ ra cấu hình

Không hard-code các giá trị sau trong service:

- Ngưỡng biến động cân nặng nhanh.
- Số ngày nhật ký tối thiểu.
- Ngưỡng tuân thủ.
- Bước tăng/giảm kcal.
- Giới hạn kcal an toàn.

Mỗi bộ quy tắc nên có version để giải thích lại kết quả cũ.

### 7. Tạo bù thông báo bị bỏ lỡ

Scheduler không nên phụ thuộc vào việc chạy đúng một ngày cụ thể. Nếu backend ngừng hoạt động, khi khởi động lại phải tạo được thông báo còn thiếu mà không tạo trùng.

### 8. Retry feedback AI có giới hạn

Bổ sung:

- `feedback_attempts`
- `last_feedback_error`
- `next_retry_at`
- Tối đa 2–3 lần thử

Check-in vẫn phải hoạt động bình thường khi Ollama ngoại tuyến.

### 9. Khóa scheduler khi chạy nhiều worker

Nếu có nhiều instance backend, chỉ một worker được xử lý cùng một check-in tại một thời điểm. Có thể dùng PostgreSQL advisory lock, Redis lock hoặc tách scheduler thành worker riêng.

### 10. Bổ sung test API

Các trường hợp tối thiểu:

- Không truy cập được check-in của user khác.
- User thường không gọi được endpoint mô phỏng.
- Production không có endpoint mô phỏng.
- Không mở lại báo cáo sau khi đã có quyết định.
- Cân nặng thay đổi quá 20% trả `422`.
- Request lặp hoặc đồng thời không tạo kỳ, metric hay plan version trùng.

## P2 — Phát triển trải nghiệm

- Việt hóa `LOSE_WEIGHT`, `MAINTAIN`, `GAIN_MUSCLE` trên giao diện.
- Giải thích ngắn cách tính khoảng cân nặng kỳ vọng.
- Hiển thị số ngày có nhật ký, ví dụ `8/14 ngày`.
- Phân biệt dữ liệu tự khai với dữ liệu hệ thống ghi nhận.
- Thêm biểu đồ cân nặng qua các kỳ.
- Hiển thị rõ feedback AI chỉ là phần diễn giải, không phải chẩn đoán y tế.

## Thứ tự đề xuất

1. Sửa tính nhất quán cân nặng khi reopen.
2. Thêm audit cho chỉnh sửa báo cáo.
3. Thay cơ chế sửa ngày của demo.
4. Khóa demo tool bằng `ENABLE_DEMO_TOOLS=false`.
5. Hoàn thiện migration runner.
6. Làm lần lượt các mục P1 và P2.

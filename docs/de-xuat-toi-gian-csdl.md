# Đề xuất tối giản CSDL NutriSmart Agent

## 1. Mục tiêu

Tài liệu này đề xuất các thuộc tính có thể lược bỏ khỏi CSDL NutriSmart Agent để:

- Giảm dữ liệu trùng lặp hoặc có thể suy ra.
- Làm ERD dễ đọc và dễ giải thích khi bảo vệ đồ án.
- Không làm mất các chức năng cốt lõi: hồ sơ sức khỏe, theo dõi dinh dưỡng, AI chat, lộ trình và check-in.

Nguyên tắc chung: chỉ lưu dữ liệu nguồn hoặc dữ liệu lịch sử cần tra cứu; hạn chế lưu dữ liệu có thể tính lại dễ dàng.

## 2. Các thuộc tính nên lược bỏ trước

Đây là nhóm ít ảnh hưởng nhất đến chức năng hiện tại.

| STT | Bảng | Thuộc tính có thể bỏ | Lý do |
|---:|---|---|---|
| 1 | `nutrition_plans` | `parent_plan_id` | Đã có `user_id` và `version` để xác định thứ tự phiên bản. |
| 2 | `activity_levels` | `description` | Tính TDEE chỉ cần `name` và `calorie_multiplier`; mô tả có thể đặt trên giao diện. |
| 3 | `role_permissions` | `created_at`, `updated_at` | Bảng chỉ có ba dòng quyền theo role và chưa cần lịch sử chỉnh sửa riêng. |
| 4 | `staff_profiles` | `gender`, `birth_date` | Có thể lấy từ `user_profile`, tránh lưu trùng thông tin cá nhân. |
| 5 | `doc_chunks` | `token_count` | Logic truy hồi hiện tại không sử dụng. |
| 6 | `doc_chunks` | `metadata` | Chưa có nghiệp vụ đọc trường này. |
| 7 | `chat_sessions` | `title` | Hệ thống hiện dùng một phiên chat cuộn cho mỗi người dùng. |
| 8 | `chat_messages` | `flagged` | Chưa có luồng kiểm duyệt hoặc cắm cờ tin nhắn thực tế. |
| 9 | `message_citations` | `rank` | Có thể xếp hạng bằng `score DESC`. |
| 10 | `exercises` | `category` | Tính calorie chỉ cần `name` và `met_value`. |
| 11 | `activity_logs` | `ended_at` | Có thể suy ra từ `started_at + duration_min`. |
| 12 | `notifications` | `dedupe_key` | Chỉ cần khi job có nguy cơ tạo thông báo trùng và cần chống trùng ở DB. |
| 13 | `audit_logs` | `ip_address` | Backend hiện chưa truyền địa chỉ IP khi ghi audit. |

## 3. Các thuộc tính có thể bỏ nhưng sẽ làm giảm chức năng

Chỉ nên bỏ khi nhóm xác nhận không cần nghiệp vụ liên quan.

| Bảng | Thuộc tính | Ảnh hưởng khi bỏ |
|---|---|---|
| `user_profile` | `custom_conditions` | Không thể nhập bệnh ngoài danh mục. |
| `user_profile` | `custom_allergens` | Không thể nhập dị nguyên ngoài danh mục và mức độ tự khai. |
| `staff_profiles` | `specialization` | Không còn thông tin chuyên môn của chuyên gia. |
| `staff_profiles` | `qualification` | Không còn thông tin bằng cấp. |
| `staff_profiles` | `employment_status` | Không thể ngừng hoạt động nhân viên mà vẫn giữ tài khoản. |
| `nutrition_plans` | `status` | Không phân biệt kế hoạch đang áp dụng, đã sửa hay hoàn tất. |
| `nutrition_plans` | `end_date` | Không xác định trực tiếp thời hạn kế hoạch. |
| `documents` | `raw_text` | Không thể xem lại toàn văn đã xử lý khi nguồn gốc bị mất. |
| `documents` | `deleted_at` | Mất chức năng xóa mềm tài liệu. |
| `documents` | `approved_by`, `approved_at` | Mất dấu vết chuyên gia duyệt tài liệu. |
| `foods` | `protein_g`, `carb_g`, `fat_g` | Chỉ còn quản lý calorie, không theo dõi chất dinh dưỡng đa lượng. |
| `meal_images` | `raw_prediction` | Mất kết quả phân tích chi tiết từ AI Vision. |
| `meal_logs` | `meal_image_id` | Không truy ngược nhật ký về ảnh món ăn. |
| `meal_logs` | `quantity` | Không hỗ trợ nhiều khẩu phần. |
| `audit_logs` | `before_data`, `after_data` | Chỉ biết có thao tác, không biết dữ liệu thay đổi thế nào. |

## 4. Các thuộc tính không nên bỏ

| Bảng | Thuộc tính | Lý do cần giữ |
|---|---|---|
| `nutrition_plans` | `version` | Xác định rõ lịch sử điều chỉnh lộ trình và đang được code sử dụng. |
| `nutrition_plans` | `content` | Nội dung thực đơn/lộ trình chính. |
| `body_metrics_history` | `recorded_at` | Cần để theo dõi sự thay đổi thể trạng theo thời gian. |
| `body_metrics_history` | `height_cm`, `weight_kg` | Dữ liệu nguồn để tính BMI tại từng mốc. |
| `activity_levels` | `calorie_multiplier` | Hệ số tính TDEE, thay thế dữ liệu hard-code. |
| `role_permissions` | Các cờ quyền | Cần cho phân quyền theo role. |
| `meal_logs` | `calories_kcal`, `log_date` | Dữ liệu cốt lõi cho nhật ký và thống kê hằng ngày. |
| `doc_chunks` | `content`, `embedding` | Dữ liệu cốt lõi của RAG. |
| `message_citations` | `message_id`, `chunk_id`, `score` | Liên kết câu trả lời AI với nguồn tham khảo và độ liên quan. |

Nên bổ sung ràng buộc cho phiên bản kế hoạch:

```sql
ALTER TABLE nutrition_plans
ADD CONSTRAINT uq_nutrition_plans_user_version UNIQUE (user_id, version);

ALTER TABLE nutrition_plans
ADD CONSTRAINT ck_nutrition_plans_version_positive CHECK (version >= 1);
```

## 5. Đề xuất tối giản `plan_checkins`

`plan_checkins` hiện là bảng nhiều thuộc tính nhất vì đang trộn bốn loại dữ liệu:

1. Thông tin chu kỳ.
2. Snapshot mục tiêu đầu kỳ.
3. Dữ liệu người dùng nhập khi check-in.
4. Kết quả đánh giá và trạng thái workflow.

### 5.1. Các thuộc tính có thể bỏ

| Thuộc tính | Cách thay thế hoặc lý do |
|---|---|
| `previous_checkin_id` | Tìm kỳ trước bằng `series_id` và `period_number - 1`. |
| `user_id` | Có thể suy ra qua `series_id`; chỉ bỏ nếu chấp nhận join thêm. |
| `goal_snapshot` | Có thể lấy từ series hoặc plan. |
| `activity_target_snapshot` | Có thể lấy từ profile/plan nếu không cần lịch sử tuyệt đối. |
| `prediction_rule_version` | Không cần nếu đồ án chỉ có một thuật toán dự đoán. |
| `baseline_waist_cm`, `actual_waist_cm` | Bỏ nếu không theo dõi vòng eo. |
| `energy_level`, `hunger_level`, `sleep_quality` | Bỏ nếu đánh giá chỉ dựa vào cân nặng, calorie và mức tuân thủ. |
| `notes` | Bỏ nếu không cần ghi chú tự do. |
| `data_quality_result` | Có thể tính lại từ số ngày nhật ký. |
| `adherence_result` | Có thể tính lại từ `adherence_pct`. |
| `feedback_status` | Có thể suy ra: có `ai_feedback` nghĩa là đã sinh phản hồi. |
| `adjusted_plan_id` | Có thể tìm phiên bản plan tiếp theo. |
| `proposed_kcal_target` | Không cần nếu giá trị cuối đã nằm trong plan mới. |
| `submitted_at`, `completed_at`, `decision_at`, `adjustment_applied_at` | Có thể rút gọn còn `created_at` và `updated_at` nếu không cần audit từng bước. |

### 5.2. Schema tối giản đề xuất

```text
plan_checkins
- id
- series_id
- plan_id
- period_number
- start_date
- period_end
- due_date
- grace_until
- baseline_weight_kg
- actual_weight_kg
- adherence_pct
- meal_log_days
- avg_kcal_intake
- weight_change_kg
- outcome_result
- safety_flags
- recommendation
- ai_feedback
- status
- decision
- created_at
- updated_at
```

Không nên rút gọn bảng này ngay lập tức nếu vẫn muốn giữ toàn bộ luồng coaching 14 ngày hiện tại. Việc bỏ thuộc tính cần đi kèm sửa service, schema API, frontend và test.

## 6. Phương án tối giản khuyến nghị

Để giảm độ phức tạp nhưng hạn chế rủi ro, nên thực hiện theo ba đợt:

### Đợt 1 — Ít ảnh hưởng

- Bỏ `nutrition_plans.parent_plan_id`.
- Bỏ `activity_levels.description`.
- Bỏ `role_permissions.created_at`, `updated_at`.
- Bỏ `staff_profiles.gender`, `birth_date`.
- Bỏ `doc_chunks.token_count`, `metadata`.
- Bỏ `chat_sessions.title`, `chat_messages.flagged`.
- Bỏ `message_citations.rank`.
- Bỏ `exercises.category`.
- Bỏ `activity_logs.ended_at`.
- Bỏ `audit_logs.ip_address` nếu xác nhận không dùng.

### Đợt 2 — Tối giản check-in

- Bỏ các snapshot và kết quả dẫn xuất không cần lưu.
- Giữ dữ liệu đầu vào quan trọng và kết quả cuối.
- Chạy lại toàn bộ test check-in trước khi triển khai.

### Đợt 3 — Chỉ khi cắt chức năng

- Bỏ dữ liệu macro của thực phẩm nếu ứng dụng chỉ theo dõi calorie.
- Bỏ custom conditions/allergens nếu chỉ dùng danh mục cố định.
- Bỏ audit chi tiết nếu không cần truy vết.
- Bỏ dữ liệu Vision chi tiết nếu chỉ cần kết quả bữa ăn cuối.

## 7. Kết luận

Không nên xóa hàng loạt chỉ để ERD ít cột. Phương án phù hợp nhất là bỏ trước các dữ liệu trùng, không được sử dụng hoặc dễ suy ra; giữ nguyên dữ liệu lịch sử và dữ liệu nguồn quan trọng.

Đặc biệt:

- Giữ `nutrition_plans.version`.
- Có thể bỏ `nutrition_plans.parent_plan_id`.
- `plan_checkins` là nơi có tiềm năng tối giản lớn nhất, nhưng cũng có rủi ro làm hỏng nghiệp vụ cao nhất.
- Mỗi đợt xóa cột cần có migration bảo toàn dữ liệu, cập nhật backend/frontend và chạy test với PostgreSQL thật.

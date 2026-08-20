# Kế hoạch triển khai Chương trình Dinh dưỡng Cá nhân hóa NutriSmart

## 1. Phạm vi và quyết định đã chốt

Tính năng được triển khai theo mô hình **Chương trình dinh dưỡng dài hạn**, thay vì coi
mỗi thực đơn 7 ngày là một lộ trình độc lập.

- Người dùng chọn thời gian chương trình khi tạo lộ trình lần đầu hoặc chủ động bắt đầu
  chương trình mới.
- Thời gian cho phép: từ **1 đến 12 tháng chương trình**.
- Một tháng chương trình được quy ước là **4 tuần (28 ngày)** để khớp chính xác với
  thực đơn 7 ngày và chu kỳ check-in 14 ngày.
- Giá trị mặc định trên giao diện là **3 tháng**.
- AI vẫn sinh một mẫu thực đơn **7 ngày**; mẫu này được lặp lại theo tuần trong suốt
  chương trình.
- Mỗi **Đợt** kéo dài 14 ngày và kết thúc bằng một lần check-in.
- Trên giao diện dùng cách gọi `Đợt 1`, `Đợt 2`, ... thay cho việc lặp lại cụm từ
  `Check-in 14 ngày` ở mọi vị trí.
- Tiến độ được lưu theo **ngày lịch thực tế**, không lưu theo vị trí 0–6 của mẫu thực đơn.
- Mọi UI text và comment mới phải viết bằng tiếng Việt.

Ví dụ chương trình 3 tháng:

```text
Chương trình 3 tháng = 84 ngày
├── Đợt 1: ngày 1–14
├── Đợt 2: ngày 15–28
├── Đợt 3: ngày 29–42
├── Đợt 4: ngày 43–56
├── Đợt 5: ngày 57–70
└── Đợt 6: ngày 71–84
```

Thời hạn là **thời gian theo dõi dự kiến**, không phải cam kết người dùng chắc chắn đạt
mục tiêu sức khỏe trong khoảng thời gian đã chọn.

---

## 2. Khái niệm nghiệp vụ

### 2.1. Chương trình

`PlanCheckinSeries` đại diện cho một chương trình đồng hành liên tục của người dùng.
Chương trình lưu:

- Mục tiêu sức khỏe.
- Ngày bắt đầu.
- Số tháng chương trình, từ 1 đến 12.
- Ngày kết thúc dự kiến.
- Trạng thái chương trình.
- Các Đợt check-in thuộc chương trình.
- Các phiên bản `NutritionPlan` được sử dụng trong chương trình.

Một chương trình 1 tháng có 2 Đợt; chương trình 12 tháng có 24 Đợt.

### 2.2. Phiên bản lộ trình

`NutritionPlan` tiếp tục là một phiên bản thực đơn và vận động do AI sinh ra.

- Mỗi phiên bản chứa mẫu 7 ngày.
- Điều chỉnh được người dùng chấp nhận sau check-in tạo một phiên bản plan mới nhưng
  **không reset thời hạn chương trình**.
- Plan cũ chuyển sang `REVISED`; lịch sử tiến độ và nhật ký liên quan vẫn được giữ lại.

Ngày hiệu lực của từng phiên bản được quản lý như sau:

- Plan ACTIVE đầu tiên có `start_date` bằng ngày bắt đầu chương trình và `end_date` tạm
  bằng `planned_end_date`.
- Khi áp dụng điều chỉnh, `end_date` của plan cũ được chốt bằng ngày trước khi plan mới
  có hiệu lực.
- Plan version mới có `start_date` bằng ngày mở Đợt tiếp theo và `end_date` tạm bằng
  `planned_end_date`.
- Khi chương trình hoàn thành tự nhiên, plan ACTIVE cuối cùng chuyển sang `COMPLETED`.

### 2.3. Đợt theo dõi

Mỗi `PlanCheckin` là một Đợt 14 ngày:

- Ngày đầu: `start_date`.
- Ngày cuối ghi nhận dữ liệu: `period_end = start_date + 13 ngày`.
- Ngày mở check-in: `due_date = start_date + 14 ngày`.
- Sau khi người dùng chốt quyết định, hệ thống mở Đợt tiếp theo nếu chương trình chưa
  kết thúc.

Giao diện hiển thị theo dạng:

```text
Đợt 2 · 03/09/2026 – 16/09/2026
Check-in Đợt 2 mở ngày 17/09/2026
Đã hoàn thành 2/6 đợt
```

### 2.4. Ánh xạ mẫu 7 ngày sang ngày thực tế

Ngày thực tế trong mỗi Đợt được ánh xạ về mẫu thực đơn bằng công thức:

```text
template_day_index = số ngày tính từ đầu chương trình % 7
```

Vì vậy ngày 8 dùng lại mẫu của ngày 1, ngày 9 dùng mẫu của ngày 2, v.v.

---

## 3. Tạo chương trình và tạo lộ trình mới

### 3.1. Không hỏi thời hạn trong form đăng ký

Form đăng ký chỉ thu thập tài khoản và hồ sơ sức khỏe. Thời hạn chương trình được hỏi
khi người dùng tạo lộ trình lần đầu để tránh kéo dài onboarding và để dữ liệu nằm đúng
ngữ cảnh nghiệp vụ.

### 3.2. Tạo chương trình lần đầu

Khi chưa có chương trình đang hoạt động, màn hình tạo lộ trình yêu cầu:

- Chiều cao hiện tại.
- Cân nặng hiện tại.
- Thời gian chương trình từ 1 đến 12 tháng.

Các lựa chọn nhanh:

```text
[1 tháng] [3 tháng] [6 tháng] [12 tháng]
[Thời gian khác: 1–12 tháng]
```

Giao diện phải hiển thị trước:

- Ngày bắt đầu.
- Ngày kết thúc dự kiến.
- Tổng số Đợt check-in.
- Ghi chú `1 tháng chương trình tương ứng 4 tuần`.

### 3.3. Bắt đầu chương trình mới khi đang có chương trình ACTIVE

Nút hiện tại được đổi từ **Tạo lộ trình mới** thành **Bắt đầu chương trình mới** để
thể hiện đúng mức độ ảnh hưởng.

Modal xác nhận hiển thị:

> Chương trình hiện tại sẽ được kết thúc và lưu vào lịch sử. Đợt đang mở sẽ bị hủy,
> nhưng các ngày đã ghi nhận và dữ liệu Nhật ký sẽ được giữ nguyên.

Modal yêu cầu nhập lại:

- Chiều cao.
- Cân nặng.
- Thời gian chương trình mới.

Chỉ khi job sinh plan mới hoàn thành thành công, backend mới:

1. Chuyển plan ACTIVE cũ sang `REVISED`.
2. Đóng chương trình cũ.
3. Chuyển Đợt `OPEN` cũ sang `CANCELLED`.
4. Tạo chương trình, plan và Đợt 1 mới.

Nếu AI/job lỗi, chương trình và plan cũ vẫn phải ACTIVE.

Nếu người dùng đã gửi check-in nhưng chưa chọn `CONTINUE` hoặc `APPLY_ADJUSTMENT`,
hệ thống chặn bắt đầu chương trình mới và yêu cầu chốt quyết định trước.

### 3.4. Hiệu chỉnh plan trong cùng chương trình

Plan chỉ được thay phiên bản trong cùng chương trình qua quyết định
`APPLY_ADJUSTMENT` ở cuối một Đợt. Việc này:

- Giữ nguyên `planned_end_date`.
- Giữ nguyên chuỗi chương trình.
- Tạo plan version mới.
- Mở Đợt tiếp theo với plan version mới.

Cập nhật cân nặng thông thường tại Hồ sơ/Nhật ký không tự ý reset chương trình hoặc
sinh plan giữa Đợt.

---

## 4. Kiểm tra số đo và rào chắn chống nhập nhầm

Gọi `W_cũ` là cân nặng gần nhất trước khi mở modal và `W_mới` là giá trị vừa nhập:

```text
0.90 × W_cũ ≤ W_mới ≤ 1.10 × W_cũ
```

Quy tắc này được gọi là **rào chắn chống nhập nhầm**, không mô tả như một chẩn đoán
hay quy tắc y khoa độc lập.

Yêu cầu:

- Frontend kiểm tra realtime và hiển thị khoảng hợp lệ.
- Backend bắt buộc kiểm tra lại; không được tin validation phía frontend.
- Vẫn áp dụng giới hạn cân nặng 20–300 kg, chiều cao 50–250 cm và BMI 10–80.
- Nếu lệch hơn 10%, khóa nút tạo chương trình và hướng dẫn người dùng xác nhận/cập nhật
  số đo tại Hồ sơ trước.
- Baseline so sánh phải là bản ghi `BodyMetricHistory` tồn tại trước request, không phải
  bản ghi vừa được cập nhật trong cùng request.

Không để frontend gọi riêng `PUT /auth/me` rồi mới gọi `/plans/generate`. Request tạo
chương trình gửi số đo, thời hạn, xác nhận và active plan dự kiến trong cùng payload:

```json
{
  "height_cm": 170,
  "weight_kg": 70.5,
  "duration_months": 3,
  "confirm_recreate": true,
  "expected_active_plan_id": "uuid-hoặc-null"
}
```

Backend chịu trách nhiệm validate, cập nhật số đo, tính lại calorie target và tạo snapshot
cho job. `expected_active_plan_id` ngăn hai tab hoặc hai request đồng thời ghi đè nhau.

---

## 5. Dữ liệu mẫu thực đơn và vận động

### 5.1. Bữa ăn

Mỗi ngày có đúng 3 bữa:

```json
{
  "type": "Sáng",
  "name": "Phở bò",
  "kcal": 450
}
```

### 5.2. Vận động

Không lưu vận động dưới dạng một chuỗi tự do. Dữ liệu mới có cấu trúc:

```json
{
  "name": "Đi bộ nhanh",
  "duration_min": 30,
  "calories_kcal": 180
}
```

- `duration_min`: từ 1 đến 600 phút.
- `calories_kcal`: từ 1 đến 5000 kcal và được hiển thị là giá trị ước tính.
- Generator và fallback đều phải trả về cùng cấu trúc.
- Backend tiếp tục đọc được plan cũ có `exercise` dạng chuỗi để không làm hỏng dữ liệu
  đã tồn tại; plan mới luôn dùng object có cấu trúc.

---

## 6. Tiến độ hàng ngày

### 6.1. Ý nghĩa của checkbox

Tick một mục nghĩa là người dùng xác nhận đã thực hiện đúng hoặc gần đúng nội dung và
khẩu phần/bài tập được đề xuất. Khi đó hệ thống đồng bộ snapshot kcal vào Nhật ký.

Nếu người dùng ăn hoặc tập khác đáng kể, họ ghi dữ liệu thực tế tại Nhật ký thay vì tick
mục tương ứng trong Plan.

Mỗi ngày có bốn item key ổn định:

```text
meal:0
meal:1
meal:2
exercise
```

### 6.2. Quy tắc ngày được phép thao tác

- Ngày tương lai chỉ được xem trước, không được cập nhật.
- Cho phép cập nhật ngày hiện tại và ngày quá khứ trong Đợt đang `OPEN`, kể cả ngày
  đã được ghi nhận.
- `COMPLETED` ở cấp ngày có nghĩa là đã ghi nhận, không đồng nghĩa với khóa chỉnh sửa.
- Khi check-in đã được gửi, bị bỏ lỡ hoặc Đợt bị hủy, toàn bộ ngày của Đợt chuyển
  sang read-only.
- Tất cả phép tính ngày dùng múi giờ `Asia/Bangkok`.

### 6.3. Nút Lưu

Nút **Lưu** gửi toàn bộ tập item đang được chọn của ngày:

- Upsert trạng thái checkbox.
- Tạo MealLog/ActivityLog cho item vừa được tick.
- Xóa đúng log do Plan tạo cho item vừa được bỏ tick.
- Không tạo bản ghi trùng khi bấm Lưu nhiều lần.
- Trả về chênh lệch kcal đã thêm/xóa để hiển thị toast.

Thông báo mẫu:

> Đã lưu tiến độ ngày 3. Nhật ký được cập nhật +820 kcal nạp và -180 kcal tiêu hao.

### 6.4. Nút Ghi nhận ngày

**Ghi nhận = kiểm tra thiếu mục + Lưu + đồng bộ Nhật ký + đánh dấu ngày đã ghi nhận**
trong cùng một transaction.

Người dùng không cần bấm Lưu trước.

Nếu còn thiếu item, modal hiển thị chính xác tên các mục chưa tick:

> Bạn chưa hoàn thành Bữa tối và Vận động. Bạn vẫn muốn ghi nhận ngày này?

Sau khi xác nhận:

- Ngày chuyển sang `COMPLETED`.
- Nếu đủ toàn bộ item, UI hiển thị `Hoàn thành 4/4`; nếu còn thiếu, UI hiển thị
  `Đã ghi nhận x/4`.
- Ngày vẫn có thể chỉnh sửa hoặc đặt lại cho tới khi Đợt bị khóa.
- UI chuyển sang ngày gần nhất tiếp theo có thể thao tác.
- Nếu không còn ngày có thể thao tác, hiển thị tổng quan tiến độ của Đợt.

### 6.5. Nút Đặt lại ngày

Đổi tên nút **Hủy** thành **Đặt lại ngày**.

Nút hoạt động với ngày hiện tại hoặc ngày cũ trong Đợt `OPEN`, kể cả ngày đã ghi nhận,
và phải có xác nhận. Backend:

- Xóa toàn bộ checkbox của ngày.
- Xóa riêng MealLog/ActivityLog có liên kết nguồn từ ngày Plan đó.
- Không xóa log nhập tay, log Vision hoặc dữ liệu đồng bộ từ thiết bị.

---

## 7. Thiết kế dữ liệu

### 7.1. Mở rộng `plan_checkin_series`

Thêm các cột:

```text
duration_months     SMALLINT NOT NULL CHECK (duration_months BETWEEN 1 AND 12)
planned_end_date    DATE NOT NULL
completed_at        TIMESTAMPTZ NULL
completion_reason   VARCHAR(30) NULL
```

Với dữ liệu cũ, migration chọn tối thiểu `duration_months = 3`. Nếu một Đợt đã có
`period_end` muộn hơn mốc 84 ngày, tăng `duration_months` đến block 28 ngày nhỏ nhất
có thể bao phủ Đợt đó, nhưng không vượt quá 12. Sau đó tính
`planned_end_date = started_at + duration_months × 28 ngày - 1 ngày`. Dữ liệu nào đã
vượt quá 12 tháng phải dừng migration để rà soát thay vì âm thầm cắt lịch sử.

### 7.2. Bảng `plan_daily_progress`

```text
id                  UUID PRIMARY KEY
user_id             UUID NOT NULL REFERENCES users(id)
series_id           UUID NOT NULL REFERENCES plan_checkin_series(id)
checkin_id          UUID NOT NULL REFERENCES plan_checkins(id)
plan_id             UUID NOT NULL REFERENCES nutrition_plans(id)
progress_date       DATE NOT NULL
template_day_index  SMALLINT NOT NULL CHECK (template_day_index BETWEEN 0 AND 6)
checked_items       JSONB NOT NULL DEFAULT '[]'
status              VARCHAR(20) NOT NULL DEFAULT 'IN_PROGRESS'
completed_at        TIMESTAMPTZ NULL
created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()

UNIQUE(checkin_id, progress_date)
```

Giá trị hợp lệ của `status`:

- `IN_PROGRESS`
- `COMPLETED`

### 7.3. Liên kết nguồn Nhật ký

Bổ sung vào `meal_logs` và `activity_logs`:

```text
source_type          VARCHAR(20) NULL
source_progress_id   UUID NULL REFERENCES plan_daily_progress(id)
source_item_key      VARCHAR(30) NULL
item_name_snapshot   VARCHAR(200) NULL
```

Tạo unique index có điều kiện:

```text
UNIQUE(source_progress_id, source_item_key)
WHERE source_type = 'PLAN'
```

Nhật ký hiển thị `item_name_snapshot` khi không có `food_id`/`exercise_id`, đồng thời
hiển thị badge `Từ lộ trình`.

Đối với `activity_logs`:

- Activity do Plan tạo có thể có `exercise_id = NULL`, nhưng bắt buộc có
  `source_type = 'PLAN'`.
- Query đồng bộ Mobile hiện đang nhận diện bằng `exercise_id IS NULL`; phải bổ sung điều
  kiện loại trừ `source_type = 'PLAN'` để không ghi đè buổi tập từ lộ trình.
- Query Nhật ký vận động phải đọc cả bản ghi có `exercise_id IS NOT NULL` và bản ghi
  `source_type = 'PLAN'`.
- `started_at` của activity từ Plan được đặt theo `progress_date` ở múi giờ
  `Asia/Bangkok`; không suy ngày từ thời điểm request.

### 7.4. Bảo vệ chỉ một plan/chương trình ACTIVE

- Thay index plan ACTIVE hiện tại bằng **unique partial index** theo `user_id`.
- Bổ sung unique partial index bảo đảm mỗi user chỉ có một `PlanCheckinSeries` ACTIVE.
- Service vẫn khóa bản ghi phù hợp khi thay plan để tránh race condition giữa nhiều
  request hoặc nhiều worker.

### 7.5. Migration cho database đã tồn tại

Tạo migration mới tiếp theo trong `db/migrations/`. Do các file init chỉ tự chạy với
volume PostgreSQL mới, tài liệu chạy local/deploy phải có lệnh áp dụng migration cho
database hiện tại hoặc sử dụng migration runner có version.

---

## 8. API

### 8.1. Tạo chương trình/plan

```text
POST /api/v1/plans/generate
GET  /api/v1/plans/generate/{job_id}
GET  /api/v1/plans/active
```

`POST /plans/generate` nhận số đo, `duration_months`, xác nhận và
`expected_active_plan_id`. Với lần tạo đầu tiên, `confirm_recreate=false` và
`expected_active_plan_id=null`.

Job phải sử dụng snapshot request, không tự đọc lại các số đo có thể đã thay đổi sau
khi enqueue.

### 8.2. Tiến độ ngày

```text
GET    /api/v1/plans/{plan_id}/days/{date}/progress
PUT    /api/v1/plans/{plan_id}/days/{date}/progress
POST   /api/v1/plans/{plan_id}/days/{date}/complete
DELETE /api/v1/plans/{plan_id}/days/{date}/progress
```

Payload lưu:

```json
{
  "checked_items": ["meal:0", "meal:1", "exercise"]
}
```

Response tối thiểu:

```json
{
  "progress_date": "2026-08-20",
  "checked_items": ["meal:0", "meal:1", "exercise"],
  "status": "IN_PROGRESS",
  "kcal_intake_delta": 820,
  "kcal_burned_delta": 180
}
```

Tất cả thao tác cập nhật progress và log chạy trong một database transaction.

---

## 9. Giao diện Plan

Trang Plan hiển thị theo cấu trúc:

1. Thẻ chương trình: mục tiêu, thời gian, ngày bắt đầu/kết thúc và số Đợt đã hoàn thành.
2. Thẻ Đợt hiện tại: `Đợt N`, khoảng ngày và ngày mở check-in.
3. Danh sách 14 ngày của Đợt, mỗi tab hiển thị ngày lịch và số mục hoàn thành.
4. Timeline ba bữa ăn và một bài tập của ngày được chọn.
5. Cụm nút `Lưu`, `Ghi nhận ngày`, `Đặt lại ngày`.
6. Khu vực check-in cuối Đợt.

Dashboard không cần đồng bộ state trực tiếp với Plan. Sau khi API lưu thành công, mở
hoặc quay lại Dashboard phải refetch summary và hiển thị số kcal mới.

---

## 10. Kết thúc và gia hạn chương trình

Sau quyết định của Đợt cuối:

- Chương trình chuyển sang `COMPLETED`.
- Không tạo Đợt tiếp theo.
- Plan và toàn bộ tiến độ chuyển sang read-only.
- Hiển thị tổng kết toàn chương trình.

Tổng kết tối thiểu gồm:

- Cân nặng đầu và cuối chương trình.
- Tổng số ngày có nhật ký.
- Tổng số ngày đã ghi nhận.
- Tỷ lệ hoàn thành các item.
- Kcal nạp/tiêu hao trung bình.
- Danh sách kết quả check-in theo từng Đợt.

Hai hành động tiếp theo:

- **Gia hạn chương trình:** thêm số tháng còn lại và tiếp tục cùng mục tiêu, nhưng tổng
  thời hạn của một chương trình không vượt quá 12 tháng.
- **Bắt đầu mục tiêu mới:** đóng lịch sử cũ và tạo chương trình mới.

Gia hạn không xóa lịch sử và không reset số thứ tự Đợt.

---

## 11. Kế hoạch triển khai

### Giai đoạn 1 — Nền tảng dữ liệu và test

1. Viết test thất bại trước cho duration, progress, idempotency và quyền sở hữu.
2. Tạo migration mở rộng `plan_checkin_series`.
3. Tạo `plan_daily_progress` và liên kết nguồn cho các bảng log.
4. Thêm unique partial index cho plan và series ACTIVE.
5. Cập nhật model và schema Pydantic.

### Giai đoạn 2 — Chương trình dài hạn

1. Bổ sung `duration_months` vào luồng tạo chương trình.
2. Tính `planned_end_date = start_date + duration_months × 28 ngày - 1 ngày`.
3. Giới hạn số Đợt theo thời hạn chương trình.
4. Bảo đảm `APPLY_ADJUSTMENT` giữ nguyên thời hạn.
5. Hoàn thiện logic kết thúc và gia hạn.

### Giai đoạn 3 — Tạo chương trình mới an toàn

1. Hợp nhất payload số đo và tạo plan.
2. Validate rào chắn 10% ở backend.
3. Kiểm tra `expected_active_plan_id` và trạng thái check-in.
4. Chỉ đóng dữ liệu cũ sau khi plan mới sinh thành công.
5. Làm modal chọn thời hạn và xác nhận trên frontend.

### Giai đoạn 4 — Plan có cấu trúc

1. Đổi exercise từ chuỗi sang object.
2. Cập nhật prompt, JSON Schema và fallback.
3. Thêm lớp tương thích với plan cũ.
4. Kiểm thử dữ liệu AI sai cấu trúc và fallback.

### Giai đoạn 5 — Tiến độ và đồng bộ Nhật ký

1. Viết service tính delta giữa trạng thái cũ và mới.
2. Viết API Lưu/Ghi nhận/Đặt lại theo transaction.
3. Gắn provenance vào log.
4. Cập nhật Diary và Dashboard đọc snapshot từ plan.
5. Bảo vệ ngày tương lai, Đợt đã khóa và dữ liệu user khác.

### Giai đoạn 6 — Giao diện và kiểm thử hồi quy

1. Hiển thị chương trình, Đợt và 14 ngày.
2. Hoàn thiện modal cảnh báo thiếu mục.
3. Hoàn thiện toast và trạng thái loading/error.
4. Build frontend và chạy toàn bộ backend test.
5. Kiểm thử trực tiếp luồng hoàn chỉnh trên trình duyệt.

---

## 12. Tiêu chuẩn nghiệm thu

### 12.1. Thời hạn chương trình

- [ ] Không cho nhập dưới 1 hoặc trên 12 tháng.
- [ ] Mặc định là 3 tháng.
- [ ] Một tháng tạo đúng 28 ngày và 2 Đợt; 12 tháng tạo đúng 24 Đợt tối đa.
- [ ] Hiển thị đúng ngày kết thúc dự kiến và tổng số Đợt.
- [ ] Điều chỉnh plan sau check-in không reset ngày kết thúc.
- [ ] Hết Đợt cuối không tự tạo thêm Đợt.

### 12.2. Tạo chương trình mới

- [ ] Tạo lần đầu không cần xác nhận ghi đè.
- [ ] Đang có chương trình ACTIVE thì modal cảnh báo đúng ảnh hưởng.
- [ ] Check-in đã gửi nhưng chưa có quyết định thì bị chặn.
- [ ] Sai lệch cân nặng trên 10% bị chặn cả frontend và backend.
- [ ] Job lỗi không đóng plan/chương trình cũ.
- [ ] Hai request đồng thời không tạo hai plan hoặc hai series ACTIVE.

### 12.3. Lưu tiến độ

- [ ] F5 hoặc chuyển trang không mất checkbox.
- [ ] Bấm Lưu lặp lại không nhân đôi MealLog/ActivityLog hoặc kcal.
- [ ] Bỏ tick rồi Lưu xóa đúng log liên kết và cập nhật delta.
- [ ] Không thể lưu ngày tương lai hoặc ngày thuộc Đợt đã khóa.
- [ ] Ngày đã ghi nhận vẫn chỉnh sửa được trong Đợt đang mở.
- [ ] Không thể đọc/sửa progress của user khác.

### 12.4. Ghi nhận ngày

- [ ] Thiếu item thì modal liệt kê đúng tên mục thiếu.
- [ ] Ghi nhận ngày tự lưu cả thay đổi chưa bấm Lưu.
- [ ] Progress và log cùng thành công hoặc cùng rollback.
- [ ] Ngày đủ item có trạng thái `Hoàn thành 4/4`; ngày thiếu item có trạng thái
  `Đã ghi nhận x/4`.
- [ ] Đặt lại ngày đã ghi nhận đưa ngày về `IN_PROGRESS` và xóa đúng log liên kết.
- [ ] UI chuyển sang ngày tiếp theo có thể thao tác.

### 12.5. Đặt lại ngày

- [ ] Hoạt động với ngày hiện tại hoặc ngày cũ trong Đợt đang mở, kể cả ngày đã ghi nhận.
- [ ] Xóa checkbox và log được sinh từ Plan.
- [ ] Không xóa log thủ công, Vision hoặc thiết bị.
- [ ] Bấm lại nhiều lần vẫn cho kết quả nhất quán.
- [ ] Activity từ Plan không bị API đồng bộ Mobile nhận nhầm hoặc ghi đè.

### 12.6. Tương thích và hồi quy

- [ ] Plan cũ có exercise dạng chuỗi vẫn hiển thị được.
- [ ] Diary hiển thị đúng tên snapshot và badge nguồn.
- [ ] Dashboard phản ánh đúng kcal sau khi refetch.
- [ ] Check-in tổng hợp đúng nhật ký của Đợt.
- [ ] Toàn bộ ngày và ranh giới ngày đúng theo `Asia/Bangkok`.
- [ ] Backend test chạy qua với `PYTHONUTF8=1`.
- [ ] Frontend `npm run build` thành công.

---

## 13. Ngoài phạm vi phiên triển khai đầu tiên

- Chuyển hàng đợi sinh plan in-memory thành durable queue/Redis worker.
- Đồng bộ realtime Dashboard qua WebSocket.
- Cho phép người dùng sửa khẩu phần trực tiếp ngay trên item của Plan.
- Tự động chẩn đoán hoặc đưa ra cam kết y khoa từ thời hạn chương trình.
- Mobile UI cho toàn bộ luồng mới; mobile thực hiện sau khi web và API ổn định.

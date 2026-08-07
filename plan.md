# Kế hoạch phát triển Check-in tiến độ 14 ngày

## 1. Mục tiêu

Xây dựng một chu kỳ coaching thống nhất để người dùng báo cáo tiến độ sau mỗi 14 ngày. Hệ thống kết hợp snapshot đầu kỳ, dữ liệu nhật ký và dữ liệu người dùng nhập để:

- Đánh giá chất lượng dữ liệu và mức độ tuân thủ.
- Đánh giá kết quả thực tế so với khoảng kỳ vọng.
- Phát hiện dấu hiệu cần thận trọng.
- Đề xuất giữ nguyên, theo dõi thêm hoặc điều chỉnh kế hoạch.
- Chỉ tạo phiên bản kế hoạch mới sau khi người dùng xác nhận.

Gemma3 chỉ viết phản hồi dễ hiểu. Kết quả đánh giá và quyết định an toàn phải do logic xác định ở backend, không phụ thuộc vào AI.

## 2. Quyết định nghiệp vụ bắt buộc

### 2.1. Thống nhất chu kỳ 14 ngày

- Một kỳ bắt đầu ở ngày `D`, ghi nhận dữ liệu từ `D` đến `D + 13`.
- Form check-in mở ở `D + 14`.
- Cho phép nhập muộn đến hết `D + 17` (3 ngày gia hạn).
- Nội dung thực đơn vẫn gồm 7 ngày và được áp dụng lại trong tuần thứ hai.
- Không đánh giá hoặc tự sinh version kế hoạch mới ở ngày 7.
- Chỉ có một kỳ check-in chưa kết thúc cho mỗi người dùng.

### 2.2. Xử lý cơ chế 7 ngày hiện tại

Phải thay thế luồng trong `services/plan_evaluator.py`, không chạy song song hai cơ chế:

- Ngừng hiển thị khối “Đánh giá chu kỳ 7 ngày” trong `Plan.jsx`.
- Ngừng gọi `POST /plans/evaluate` từ frontend.
- Tắt job nền `run_plan_evaluation_loop()` khi tính năng 14 ngày được bật.
- Không xóa ngay bảng `plan_evaluations`; giữ để đọc lịch sử cũ và thực hiện migration dữ liệu sau nếu cần.
- Không dùng `force=true` trong production. Dữ liệu demo phải dùng đồng hồ giả hoặc endpoint chỉ bật trong môi trường development.

### 2.3. Không dùng một con số dự đoán tuyệt đối

Snapshot lưu một khoảng cân nặng kỳ vọng:

- `expected_weight_min_kg`
- `expected_weight_max_kg`

Các ngưỡng thay đổi cân nặng phải là cấu hình được chuyên gia duyệt. Không dự đoán vòng eo nếu chưa có quy tắc đã được kiểm chứng; chỉ lưu vòng eo đầu kỳ và cuối kỳ để theo dõi xu hướng.

## 3. Luồng nghiệp vụ chuẩn

```text
Người dùng tạo hoặc áp dụng kế hoạch
        ↓
Đóng kế hoạch ACTIVE cũ và hủy kỳ chưa hoàn tất của mục tiêu cũ (nếu có)
        ↓
Tạo kế hoạch ACTIVE + chuỗi coaching ACTIVE
        ↓
Tạo đúng một kỳ check-in OPEN
        ↓
Chụp snapshot bất biến tại đầu kỳ
        ↓
Người dùng áp dụng thực đơn 7 ngày trong 2 tuần và ghi nhật ký
        ↓
Ngày 12: thông báo sắp đến hạn
        ↓
Ngày 14: form chuyển sang trạng thái có thể gửi
        ↓
Người dùng submit dữ liệu thực tế
        ↓
Transaction: khóa kỳ → kiểm tra quyền/trạng thái → lưu check-in
        ↓
Upsert cân nặng vào body_metrics_history và cập nhật hồ sơ hiện tại
        ↓
Tổng hợp nhật ký 14 ngày + đánh giá bằng quy tắc backend
        ↓
Lưu kết quả và trả phản hồi tức thời, không chờ Gemma3
        ↓
Job nền sinh lời nhận xét AI; lỗi thì dùng nội dung fallback
        ↓
Người dùng xác nhận CONTINUE hoặc APPLY_ADJUSTMENT
        ↓
Tạo kỳ 14 ngày tiếp theo; chỉ tạo plan version mới nếu thực sự điều chỉnh
```

## 4. Trạng thái và chuyển trạng thái

### 4.1. Trạng thái lưu trong CSDL

`plan_checkins.status` chỉ lưu trạng thái nghiệp vụ ổn định:

- `OPEN`: kỳ hiện tại chưa được gửi.
- `COMPLETED`: đã submit và đánh giá xong.
- `MISSED`: hết thời gian gia hạn mà không submit.
- `CANCELLED`: bị hủy do đổi mục tiêu, thay kế hoạch thủ công hoặc đóng tài khoản.

`UPCOMING`, `DUE`, `OVERDUE` là trạng thái hiển thị được suy ra từ ngày hiện tại, không lưu xuống DB để tránh dữ liệu thời gian bị cũ:

```text
OPEN và today < due_date                → UPCOMING
OPEN và due_date <= today <= grace_until → DUE
OPEN và today > grace_until             → OVERDUE, sau đó reconcile thành MISSED
```

### 4.2. Quy tắc chuyển trạng thái

```text
OPEN → COMPLETED: submit hợp lệ đúng hạn hoặc trong thời gian gia hạn
OPEN → MISSED: hết grace_until
OPEN → CANCELLED: mục tiêu/kế hoạch bị thay đổi giữa kỳ
COMPLETED → không được sửa dữ liệu gốc
MISSED/CANCELLED → không được submit
```

Nếu người dùng nhập sai sau khi hoàn tất, triển khai một thao tác sửa có audit ở giai đoạn sau; không cho `POST submit` ghi đè lịch sử.

## 5. Thiết kế dữ liệu

Migration mới phải là `db/migrations/19_periodic_checkins.sql` vì repo đã có migration 18.

### 5.1. Bảng `plan_checkin_series`

Nhóm các kỳ liên tục theo cùng một mục tiêu, tránh trùng `period_number` khi đổi plan:

```sql
CREATE TABLE plan_checkin_series (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    goal        goal_enum NOT NULL,
    status      VARCHAR(20) NOT NULL DEFAULT 'ACTIVE'
                CHECK (status IN ('ACTIVE', 'CLOSED')),
    started_at  DATE NOT NULL,
    closed_at   DATE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (closed_at IS NULL OR closed_at >= started_at)
);

CREATE UNIQUE INDEX uq_active_checkin_series_per_user
ON plan_checkin_series(user_id) WHERE status = 'ACTIVE';
```

### 5.2. Bảng `plan_checkins`

```sql
CREATE TABLE plan_checkins (
    id                         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    series_id                  UUID NOT NULL REFERENCES plan_checkin_series(id) ON DELETE CASCADE,
    user_id                    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    plan_id                    UUID NOT NULL REFERENCES nutrition_plans(id) ON DELETE CASCADE,
    adjusted_plan_id           UUID REFERENCES nutrition_plans(id) ON DELETE SET NULL,
    previous_checkin_id        UUID REFERENCES plan_checkins(id) ON DELETE SET NULL,
    period_number              INT NOT NULL CHECK (period_number > 0),
    start_date                 DATE NOT NULL,
    period_end                 DATE NOT NULL,
    due_date                   DATE NOT NULL,
    grace_until                DATE NOT NULL,

    baseline_weight_kg         NUMERIC(5,2) NOT NULL CHECK (baseline_weight_kg BETWEEN 20 AND 300),
    baseline_waist_cm          NUMERIC(5,2),
    goal_snapshot              goal_enum NOT NULL,
    target_kcal_snapshot       INT NOT NULL CHECK (target_kcal_snapshot BETWEEN 1200 AND 4000),
    activity_target_snapshot   SMALLINT CHECK (activity_target_snapshot BETWEEN 1 AND 5),
    expected_weight_min_kg     NUMERIC(5,2) NOT NULL,
    expected_weight_max_kg     NUMERIC(5,2) NOT NULL,
    prediction_rule_version    VARCHAR(30) NOT NULL,

    actual_weight_kg           NUMERIC(5,2) CHECK (actual_weight_kg BETWEEN 20 AND 300),
    actual_waist_cm            NUMERIC(5,2),
    actual_activity_level      SMALLINT CHECK (actual_activity_level BETWEEN 1 AND 5),
    adherence_pct              SMALLINT CHECK (adherence_pct BETWEEN 0 AND 100),
    energy_level               SMALLINT CHECK (energy_level BETWEEN 1 AND 5),
    hunger_level               SMALLINT CHECK (hunger_level BETWEEN 1 AND 5),
    sleep_quality              SMALLINT CHECK (sleep_quality BETWEEN 1 AND 5),
    notes                      VARCHAR(1000),

    meal_log_days              SMALLINT,
    avg_kcal_intake            NUMERIC(8,2),
    weight_change_kg           NUMERIC(5,2),
    data_quality_result        VARCHAR(30),
    adherence_result           VARCHAR(20),
    outcome_result             VARCHAR(30),
    safety_flags               JSONB NOT NULL DEFAULT '[]'::jsonb,
    recommendation             VARCHAR(30),
    recommendation_reason      TEXT,
    proposed_kcal_target       INT,

    ai_feedback                TEXT,
    feedback_status            VARCHAR(20) NOT NULL DEFAULT 'NOT_REQUESTED'
                               CHECK (feedback_status IN ('NOT_REQUESTED', 'PENDING', 'COMPLETED', 'FAILED')),
    status                     VARCHAR(20) NOT NULL DEFAULT 'OPEN'
                               CHECK (status IN ('OPEN', 'COMPLETED', 'MISSED', 'CANCELLED')),
    submitted_at               TIMESTAMPTZ,
    completed_at               TIMESTAMPTZ,
    adjustment_applied_at      TIMESTAMPTZ,
    created_at                 TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                 TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (series_id, period_number),
    UNIQUE (user_id, start_date),
    CHECK (period_end = start_date + 13),
    CHECK (due_date = start_date + 14),
    CHECK (grace_until >= due_date),
    CHECK (expected_weight_min_kg <= expected_weight_max_kg),
    CHECK (actual_waist_cm IS NULL OR actual_waist_cm BETWEEN 30 AND 250),
    CHECK (baseline_waist_cm IS NULL OR baseline_waist_cm BETWEEN 30 AND 250),
    CHECK (proposed_kcal_target IS NULL OR proposed_kcal_target BETWEEN 1200 AND 4000)
);

CREATE UNIQUE INDEX uq_open_checkin_per_user
ON plan_checkins(user_id) WHERE status = 'OPEN';
CREATE INDEX ix_plan_checkins_user_due ON plan_checkins(user_id, due_date DESC);
CREATE INDEX ix_plan_checkins_feedback ON plan_checkins(feedback_status)
WHERE feedback_status = 'PENDING';
```

`updated_at` phải được cập nhật bằng trigger dùng chung hoặc SQLAlchemy `onupdate`; `DEFAULT now()` không tự thay đổi khi update.

### 5.3. Quan hệ model

Thêm `PlanCheckinSeries` và `PlanCheckin` trong `backend/app/models.py`. `plan_id` dùng `ON DELETE CASCADE` để thao tác xóa tài khoản có thể dọn toàn bộ dữ liệu cá nhân; ứng dụng không cung cấp thao tác xóa riêng một plan đã có lịch sử check-in.

## 6. Snapshot và dự đoán

Khi tạo kỳ:

1. Lấy cân nặng mới nhất từ `body_metrics_history`; nếu không có thì lấy `user.info.weight_kg`.
2. Nếu không có cân nặng hợp lệ, không tạo kỳ và yêu cầu cập nhật hồ sơ.
3. Chụp goal, kcal, activity target và plan version; các trường snapshot không bao giờ cập nhật sau đó.
4. Tính khoảng cân nặng kỳ vọng bằng hàm thuần `expected_weight_range()`.
5. Lưu `prediction_rule_version` để có thể giải thích và tái lập kết quả sau này.

Không tính dây chuyền từ dự đoán kỳ trước. Baseline kỳ mới luôn lấy từ cân nặng thực tế hợp lệ gần nhất. Nếu kỳ trước bị bỏ và cân nặng đã quá cũ, vẫn tạo kỳ nhưng đánh dấu chất lượng dự đoán thấp và nhắc cập nhật cân nặng.

## 7. Thuật toán đánh giá xác định

Tách thành các hàm thuần để viết unit test:

```python
derive_data_quality(...)
derive_adherence(...)
derive_safety_flags(...)
derive_outcome(...)
derive_recommendation(...)
propose_kcal_target(...)
```

### 7.1. Chất lượng dữ liệu

- Kết hợp `adherence_pct` tự khai với số ngày có meal log, không tin tuyệt đối một giá trị tự khai.
- `SUFFICIENT`: có cân nặng cuối kỳ và số ngày nhật ký đạt ngưỡng cấu hình.
- `PARTIAL`: có cân nặng nhưng nhật ký thiếu.
- `INSUFFICIENT`: thiếu cân nặng hoặc hầu như không có dữ liệu theo dõi.

Nếu `INSUFFICIENT`, recommendation bắt buộc là `CONTINUE_AND_TRACK`; không được chỉnh kcal.

### 7.2. Tuân thủ

Ngưỡng ban đầu phải đặt trong config và được chuyên gia duyệt, ví dụ:

- `HIGH`: từ 80%.
- `MEDIUM`: 50–79%.
- `LOW`: dưới 50%.

Nếu tuân thủ thấp, không kết luận mô hình dự đoán sai và không tự chỉnh kế hoạch.

### 7.3. Kết quả

- `WITHIN_EXPECTED_RANGE`: cân nặng nằm trong khoảng kỳ vọng.
- `BELOW_EXPECTED_RANGE`: cân nặng thấp hơn khoảng kỳ vọng.
- `ABOVE_EXPECTED_RANGE`: cân nặng cao hơn khoảng kỳ vọng.
- `NOT_EVALUATED`: dữ liệu hoặc tuân thủ không đủ.

Không xem thay đổi nhanh hơn kỳ vọng là kết quả tốt mặc định. Chỉ đề xuất chỉnh kcal khi hai kỳ liên tiếp lệch theo hướng không đạt mục tiêu; lệch theo hướng quá nhanh chỉ tiếp tục theo dõi hoặc chuyển chuyên gia.

### 7.4. An toàn

Tạo cờ an toàn bằng quy tắc cấu hình, tối thiểu gồm:

- Biến động cân nặng vượt ngưỡng đã được chuyên gia duyệt.
- Năng lượng rất thấp.
- Đói cao kéo dài.
- Giấc ngủ rất kém.
- Mục tiêu `MEDICAL` hoặc bệnh nền cần giám sát khi đề xuất thay đổi.

Nếu có safety flag nghiêm trọng:

```text
recommendation = NEEDS_REVIEW
proposed_kcal_target = NULL
```

Không cho phép áp dụng điều chỉnh tự động.

### 7.5. Recommendation

| Điều kiện | Recommendation |
|---|---|
| Có cờ an toàn nghiêm trọng | `NEEDS_REVIEW` |
| Dữ liệu không đủ | `CONTINUE_AND_TRACK` |
| Tuân thủ thấp hoặc trung bình | `IMPROVE_ADHERENCE` |
| Tuân thủ cao, đúng khoảng kỳ vọng | `CONTINUE` |
| Tuân thủ cao, lệch kỳ vọng lần đầu | `CONTINUE_AND_MONITOR` |
| Tuân thủ cao, lệch hai kỳ liên tiếp | `ADJUST_PLAN` |

`propose_kcal_target()` chỉ điều chỉnh một bước nhỏ theo config, luôn clamp trong khoảng an toàn và không chạy với mục tiêu `MEDICAL` nếu chưa được chuyên gia duyệt.

## 8. Service và transaction

Tạo `backend/app/services/plan_checkin.py` với các hàm:

- `create_series_and_first_period(db, user, plan)`
- `create_next_period(db, series, plan, previous_checkin)`
- `get_current_checkin(db, user)`
- `reconcile_overdue_checkin(db, user, today)`
- `submit_checkin(db, user, checkin_id, payload)`
- `record_checkin_weight(db, user, checkin)`
- `evaluate_checkin(db, user, checkin)`
- `record_decision(db, user, checkin_id, action)`
- `process_pending_feedback(db)`

### 8.1. Submit idempotent và chống race condition

Trong một transaction:

1. Query check-in bằng `checkin_id + user_id` với `SELECT ... FOR UPDATE`.
2. Trả `404` nếu không thuộc user hiện tại để không làm lộ ID của người khác.
3. Chỉ nhận khi trạng thái `OPEN` và `due_date <= today <= grace_until`.
4. Nếu đã `COMPLETED`, trả lại kết quả cũ thay vì tạo dữ liệu lần hai.
5. Validate payload và tính toàn bộ kết quả bằng backend.
6. Upsert `body_metrics_history` theo `(user_id, recorded_at)`.
7. Cập nhật `user.info.weight_kg` trong cùng transaction.
8. Chuyển sang `COMPLETED`, đặt `feedback_status=PENDING`, commit.

Cần unique index `(user_id, recorded_at)` cho `body_metrics_history` nếu database hiện chưa có.

### 8.2. Quyết định sau check-in

- `CONTINUE`: tạo kỳ tiếp theo với cùng plan version.
- `APPLY_ADJUSTMENT`: chỉ hợp lệ khi recommendation là `ADJUST_PLAN`, tạo đúng một plan version mới rồi tạo kỳ tiếp theo gắn với plan mới.
- `NEEDS_REVIEW`: không có nút apply; chỉ hiển thị hướng dẫn liên hệ chuyên gia.
- Mỗi check-in chỉ được xử lý quyết định một lần.
- `adjusted_plan_id` và `adjustment_applied_at` bảo đảm request lặp không tạo nhiều version.

Nếu sinh nội dung plan mới bằng Ollama thất bại, rollback việc tạo version/kỳ mới và giữ check-in ở trạng thái chờ quyết định để người dùng thử lại. Không để tồn tại plan mới mà thiếu kỳ, hoặc kỳ mới mà thiếu plan.

## 9. AI feedback không chặn check-in

Sau submit, API trả kết quả quy tắc ngay. Job nền quét các row `feedback_status=PENDING`:

1. Đọc snapshot và kết quả đã lưu.
2. Gọi Gemma3 với timeout giới hạn.
3. Chỉ yêu cầu diễn giải, không cho AI thay đổi recommendation.
4. Thành công: lưu `ai_feedback`, chuyển `COMPLETED`.
5. Thất bại: lưu phản hồi mẫu an toàn, chuyển `FAILED` và có thể retry hữu hạn.

Frontend hiển thị “Đang tạo nhận xét cá nhân hóa…” và polling nhẹ hoặc tải lại khi người dùng quay lại. Check-in không bao giờ thất bại chỉ vì Ollama chậm hoặc offline.

## 10. API

Thêm router hoặc mở rộng `backend/app/routers/plans.py`:

```http
GET  /api/v1/plans/active/checkin
GET  /api/v1/plans/checkins/history?limit=10
POST /api/v1/plans/checkins/{checkin_id}/submit
POST /api/v1/plans/checkins/{checkin_id}/decision
```

`POST /decision` nhận:

```json
{ "action": "CONTINUE" }
```

hoặc:

```json
{ "action": "APPLY_ADJUSTMENT" }
```

Mọi endpoint lấy user từ JWT. Không nhận hoặc tin `user_id`, recommendation hay proposed kcal do client gửi.

Mã lỗi cần thống nhất:

- `404`: kỳ không tồn tại hoặc không thuộc người dùng.
- `409`: trạng thái không cho phép submit/decision hoặc đã có kỳ kế tiếp.
- `422`: payload không hợp lệ.
- `503`: chỉ dùng khi tác vụ tạo plan mới thực sự không thể hoàn thành; submit check-in không trả 503 vì AI feedback.

## 11. Pydantic schema

Thêm vào `backend/app/schemas.py`:

- `CheckinSubmitIn`
- `CheckinDecisionIn`
- `PlanCheckinOut`
- `CheckinHistoryOut`

Validation:

- `actual_weight_kg`: 20–300.
- `actual_waist_cm`: tùy chọn, 30–250.
- `actual_activity_level`: 1–5.
- `adherence_pct`: 0–100.
- `energy_level`, `hunger_level`, `sleep_quality`: 1–5.
- `notes`: trim, tối đa 1.000 ký tự.
- Cấm `NaN` và số vô hạn.

## 12. Frontend

### 12.1. API layer

Thêm vào `frontend/src/lib/api.js`:

- `activeCheckin()`
- `checkinHistory(limit)`
- `submitCheckin(id, payload)`
- `decideCheckin(id, action)`

### 12.2. Trang Plan

Thay khối đánh giá 7 ngày bằng `CheckinPanel`:

- Countdown đến ngày check-in.
- Trạng thái sắp đến hạn, đến hạn, quá hạn, hoàn tất hoặc bỏ lỡ.
- Form chỉ mở khi đến hạn.
- Cân nặng và vòng eo dùng input number có giới hạn và cảnh báo đỏ.
- Activity dùng select 1–5.
- Tuân thủ dùng slider kèm số phần trăm đọc được bằng bàn phím.
- Năng lượng, đói và ngủ dùng nhóm radio 1–5, không dùng icon chỉ có thể click.
- Notes có bộ đếm `0/1000`.
- Nút submit chống double-click và giữ dữ liệu form khi chuyển trang.

Sau submit hiển thị riêng:

- Snapshot đầu kỳ.
- Kết quả thực tế.
- Chất lượng dữ liệu và mức tuân thủ.
- Khoảng kỳ vọng, không chỉ một con số dự đoán.
- Cờ an toàn nếu có.
- Recommendation và lý do từ backend.
- AI feedback hoặc trạng thái đang xử lý.
- Nút hành động đúng theo recommendation.

Không hiển thị nút “Áp dụng điều chỉnh” khi dữ liệu thiếu, tuân thủ thấp hoặc có safety flag.

### 12.3. Thông báo

Tạo notification theo cơ chế idempotent:

- Ngày 12: sắp đến hạn.
- Ngày 14: đã đến hạn.
- Trong grace period: nhắc quá hạn một lần.

Cần khóa duy nhất theo `user_id + checkin_id + notification_type` để job chạy lại không tạo thông báo trùng.

## 13. Thay đổi khi hồ sơ hoặc kế hoạch đổi giữa kỳ

- Sửa họ tên hoặc thông tin không ảnh hưởng mục tiêu: không đổi snapshot.
- Sửa cân nặng: thêm lịch sử mới nhưng không sửa baseline của kỳ hiện tại.
- Đổi goal, chiều cao, bệnh nền, dị ứng hoặc activity target có ảnh hưởng kế hoạch: cảnh báo người dùng kỳ hiện tại sẽ bị hủy.
- Sau khi xác nhận: `CANCELLED` kỳ hiện tại, đóng series cũ, tạo plan và series mới trong một transaction.
- Nếu người dùng tự tạo plan mới khi đang có kỳ `OPEN`, áp dụng cùng quy tắc hủy; không để hai kỳ mở.

## 14. Job nền và phục hồi lỗi

Job định kỳ phải an toàn khi chạy nhiều lần:

- Reconcile kỳ quá `grace_until` thành `MISSED`.
- Tạo notification chưa tồn tại.
- Xử lý feedback `PENDING` với số lần retry hữu hạn.
- Không tự điều chỉnh plan.
- Không tạo kỳ tiếp theo nếu đã tồn tại kỳ `OPEN`.

Các invariant cần kiểm tra bằng constraint và test:

- Tối đa một plan `ACTIVE` trên mỗi user.
- Tối đa một series `ACTIVE` trên mỗi user.
- Tối đa một check-in `OPEN` trên mỗi user.
- Mỗi check-in có tối đa một quyết định và một `adjusted_plan_id`.
- Không có plan điều chỉnh mà không liên kết lại check-in nguồn.

## 15. Kế hoạch triển khai theo TDD

### Giai đoạn 1: Logic thuần

1. Viết test khoảng ngày và trạng thái hiển thị.
2. Viết test dự đoán khoảng cân nặng theo từng goal.
3. Viết test data quality, adherence, outcome và safety flags.
4. Viết bảng test recommendation, gồm mọi nhánh trong mục 7.5.
5. Implement các hàm thuần cho đến khi test đạt.

### Giai đoạn 2: Database và service

1. Thêm migration 19 và models.
2. Test tạo series/kỳ đầu tiên và snapshot bất biến.
3. Test constraint chỉ một series/kỳ mở.
4. Test submit đúng hạn, nhập muộn, quá hạn và submit lặp.
5. Test quyền sở hữu giữa hai user.
6. Test upsert cân nặng cùng ngày.
7. Test transaction rollback khi một bước thất bại.

### Giai đoạn 3: Plan decision

1. Test CONTINUE tạo đúng một kỳ mới với cùng plan.
2. Test ADJUST_PLAN chỉ tạo một version mới.
3. Test request decision lặp không tạo dữ liệu trùng.
4. Test safety flag và recommendation khác không thể gọi adjustment.
5. Test Ollama lỗi không làm mất check-in.

### Giai đoạn 4: API

1. Test 401, 404, 409, 422 và happy path.
2. Test user không đọc hoặc submit check-in của user khác.
3. Test response không lộ dữ liệu nội bộ hoặc prompt AI.

### Giai đoạn 5: Frontend

1. Thay UI đánh giá 7 ngày.
2. Thêm form validation và trạng thái loading/error.
3. Thêm kết quả, lịch sử và quyết định.
4. Giữ draft form trong `sessionStorage` theo `checkin_id`.
5. Chạy `npm run build` và kiểm thử trình duyệt cho mobile/desktop.

### Giai đoạn 6: Chuyển đổi và dọn luồng cũ

1. Tắt job đánh giá 7 ngày bằng config mặc định.
2. Ẩn endpoint/nút force khỏi production.
3. Giữ lịch sử `plan_evaluations` ở chế độ chỉ đọc.
4. Seed lại demo với kỳ 14 ngày đến hạn.
5. Cập nhật tài liệu chạy và API docs.

## 16. Verification và tiêu chí nghiệm thu

### Automated

```powershell
cd backend
$env:PYTHONUTF8='1'
.\.venv\Scripts\python.exe -m pytest -q

cd ..\frontend
npm run build
```

Lưu ý: migration trong `db/migrations` chỉ tự chạy với volume PostgreSQL mới. Khi kiểm thử trên database hiện có, phải áp dụng migration 19 theo quy trình migration an toàn; không xóa volume nếu chưa được người dùng cho phép.

### Kịch bản bắt buộc

1. Tạo plan lần đầu sinh đúng một series và một kỳ OPEN.
2. Trước due date không thể submit.
3. Đúng due date submit thành công và cập nhật cân nặng đúng một lần.
4. Submit lặp không tạo body metric hoặc kết quả trùng.
5. User A không truy cập được check-in của user B.
6. Thiếu nhật ký không được đề xuất chỉnh kcal.
7. Tuân thủ thấp không bị kết luận prediction sai.
8. Có safety flag không xuất hiện nút adjustment.
9. Hai kỳ lệch liên tiếp và tuân thủ cao mới đề xuất adjustment.
10. APPLY_ADJUSTMENT tạo đúng một plan version và một kỳ tiếp theo.
11. Gemma3 timeout vẫn hoàn tất check-in với phản hồi fallback.
12. Đổi goal giữa kỳ hủy đúng kỳ/series cũ và không để hai kỳ OPEN.
13. Quá grace period chuyển MISSED và không cho submit.
14. Job và notification chạy lặp không tạo bản ghi trùng.
15. UI giữ draft khi chuyển trang và hiển thị lỗi tiếng Việt rõ ràng.

## 17. Definition of Done

Tính năng chỉ hoàn tất khi:

- Không còn luồng đánh giá 7 ngày có thể tự sinh plan song song.
- Mọi nhánh đánh giá quan trọng có unit test.
- Constraint DB bảo vệ các invariant, không chỉ dựa vào frontend.
- Submit và adjustment idempotent, có transaction và kiểm tra ownership.
- Check-in không phụ thuộc vào việc Gemma3 đang online.
- Các trường hợp đổi mục tiêu, bỏ kỳ, nhập trễ và request đồng thời đã được test.
- Backend test đạt, frontend build đạt và luồng được kiểm thử trong trình duyệt.
- UI và thông báo đều bằng tiếng Việt.

## 18. Git workflow đề xuất

- Sau khi nhánh sửa validation hiện tại được merge, tạo nhánh `feat/14-day-checkin` từ `main` mới nhất.
- Không phát triển tính năng này trực tiếp trên `fix/input-validation-ux`.
- Triển khai theo từng commit nhỏ: logic → migration/model → service/API → frontend → cleanup luồng 7 ngày.
- Chỉ commit sau khi test tương ứng đạt; tích hợp qua Pull Request.

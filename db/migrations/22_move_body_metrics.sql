-- Chuyển số đo có thể thay đổi khỏi user_info sang bảng lịch sử.
ALTER TABLE body_metrics_history
    ADD COLUMN IF NOT EXISTS height_cm NUMERIC(5, 2)
        CHECK (height_cm > 50 AND height_cm < 250);

-- Bổ sung chiều cao cho các mốc cân nặng đã có trước đây.
UPDATE body_metrics_history bmh
SET height_cm = ui.height_cm
FROM user_info ui
WHERE bmh.user_id = ui.user_id
  AND bmh.height_cm IS NULL;

-- Ghi số đo hiện tại thành mốc hôm nay. Việc này cũng bảo toàn các lần cập nhật
-- hồ sơ trước đây vốn chỉ ghi vào user_info mà chưa tạo lịch sử.
INSERT INTO body_metrics_history (user_id, recorded_at, height_cm, weight_kg)
SELECT ui.user_id, CURRENT_DATE, ui.height_cm, ui.weight_kg
FROM user_info ui
WHERE (ui.height_cm IS NOT NULL OR ui.weight_kg IS NOT NULL)
ON CONFLICT (user_id, recorded_at) DO UPDATE
SET height_cm = COALESCE(EXCLUDED.height_cm, body_metrics_history.height_cm),
    weight_kg = COALESCE(EXCLUDED.weight_kg, body_metrics_history.weight_kg);

ALTER TABLE user_info DROP COLUMN IF EXISTS height_cm;
ALTER TABLE user_info DROP COLUMN IF EXISTS weight_kg;

-- BMI là dữ liệu dẫn xuất, model tính động từ số đo tại từng mốc.
ALTER TABLE body_metrics_history DROP COLUMN IF EXISTS bmi;

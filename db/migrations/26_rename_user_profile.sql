-- Đồng bộ tên hồ sơ người dùng trong schema hiện hành.
DO $$
BEGIN
    IF to_regclass('public.user_info') IS NOT NULL
       AND to_regclass('public.user_profile') IS NULL THEN
        ALTER TABLE user_info RENAME TO user_profile;
    END IF;
END $$;

-- BMI hiện được tính động từ mốc số đo mới nhất trong body_metrics_history.
ALTER TABLE user_profile DROP COLUMN IF EXISTS bmi;

-- PostgreSQL tự cập nhật các khóa ngoại khi bảng được rename.
CREATE OR REPLACE VIEW v_daily_summary AS
SELECT
    u.id AS user_id,
    d.day,
    COALESCE(m.kcal_in, 0) AS kcal_intake,
    COALESCE(a.kcal_out, 0) AS kcal_burned,
    up.daily_calorie_target,
    up.daily_calorie_target - COALESCE(m.kcal_in, 0) + COALESCE(a.kcal_out, 0)
        AS kcal_remaining
FROM users u
CROSS JOIN LATERAL (
    SELECT generate_series(CURRENT_DATE - 30, CURRENT_DATE, '1 day')::date AS day
) d
LEFT JOIN user_profile up ON up.user_id = u.id
LEFT JOIN LATERAL (
    SELECT SUM(calories_kcal) AS kcal_in FROM meal_logs ml
    WHERE ml.user_id = u.id AND ml.log_date = d.day
) m ON TRUE
LEFT JOIN LATERAL (
    SELECT SUM(calories_burned) AS kcal_out FROM activity_logs al
    WHERE al.user_id = u.id
      AND DATE(COALESCE(al.started_at, al.logged_at) AT TIME ZONE 'Asia/Bangkok') = d.day
) a ON TRUE;

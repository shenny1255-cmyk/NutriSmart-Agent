CREATE OR REPLACE VIEW v_daily_summary AS
SELECT
    u.id AS user_id,
    d.day,
    COALESCE(m.kcal_in, 0)  AS kcal_intake,
    COALESCE(a.kcal_out, 0) AS kcal_burned,
    hp.daily_calorie_target,
    hp.daily_calorie_target - COALESCE(m.kcal_in, 0) + COALESCE(a.kcal_out, 0)
        AS kcal_remaining
FROM users u
CROSS JOIN LATERAL (
    SELECT generate_series(CURRENT_DATE - 30, CURRENT_DATE, '1 day')::date AS day
) d
LEFT JOIN health_profiles hp ON hp.user_id = u.id
LEFT JOIN LATERAL (
    SELECT SUM(calories_kcal) AS kcal_in FROM meal_logs ml
    WHERE ml.user_id = u.id AND ml.log_date = d.day
) m ON TRUE
LEFT JOIN LATERAL (
    SELECT SUM(calories_burned) AS kcal_out FROM activity_logs al
    WHERE al.user_id = u.id AND al.log_date = d.day
) a ON TRUE;
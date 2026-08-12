-- Migration 18: Tái cấu trúc CSDL theo mô hình Table-per-Role Pattern (24 Bảng)

-- 1. Bổ sung các cột sức khỏe vào user_info
ALTER TABLE user_info ADD COLUMN IF NOT EXISTS gender VARCHAR(10);
ALTER TABLE user_info ADD COLUMN IF NOT EXISTS birth_date DATE;
ALTER TABLE user_info ADD COLUMN IF NOT EXISTS height_cm NUMERIC(5, 2);
ALTER TABLE user_info ADD COLUMN IF NOT EXISTS weight_kg NUMERIC(5, 2);
ALTER TABLE user_info ADD COLUMN IF NOT EXISTS activity_level SMALLINT;
ALTER TABLE user_info ADD COLUMN IF NOT EXISTS goal VARCHAR(20) DEFAULT 'MAINTAIN';
ALTER TABLE user_info ADD COLUMN IF NOT EXISTS daily_calorie_target INTEGER;

-- Migrate dữ liệu từ health_profiles sang user_info (nếu health_profiles còn tồn tại)
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'health_profiles') THEN
        UPDATE user_info ui
        SET 
            gender = hp.gender,
            birth_date = hp.birth_date,
            height_cm = hp.height_cm,
            weight_kg = hp.weight_kg,
            activity_level = hp.activity_level,
            goal = hp.goal,
            daily_calorie_target = hp.daily_calorie_target
        FROM health_profiles hp
        WHERE ui.user_id = hp.user_id;
    END IF;
END $$;

-- 2. Cập nhật Khóa ngoại cho profile_conditions & profile_allergens nối trực tiếp với user_info.user_id
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.columns WHERE table_name = 'profile_conditions' AND column_name = 'profile_id') THEN
        ALTER TABLE profile_conditions RENAME COLUMN profile_id TO user_id;
    END IF;
    IF EXISTS (SELECT FROM information_schema.columns WHERE table_name = 'profile_allergens' AND column_name = 'profile_id') THEN
        ALTER TABLE profile_allergens RENAME COLUMN profile_id TO user_id;
    END IF;
END $$;

ALTER TABLE profile_conditions DROP CONSTRAINT IF EXISTS profile_conditions_profile_id_fkey;
ALTER TABLE profile_conditions DROP CONSTRAINT IF EXISTS profile_conditions_user_id_fkey;
ALTER TABLE profile_conditions ADD CONSTRAINT profile_conditions_user_id_fkey FOREIGN KEY (user_id) REFERENCES user_info(user_id) ON DELETE CASCADE;

ALTER TABLE profile_allergens DROP CONSTRAINT IF EXISTS profile_allergens_profile_id_fkey;
ALTER TABLE profile_allergens DROP CONSTRAINT IF EXISTS profile_allergens_user_id_fkey;
ALTER TABLE profile_allergens ADD CONSTRAINT profile_allergens_user_id_fkey FOREIGN KEY (user_id) REFERENCES user_info(user_id) ON DELETE CASCADE;

-- 3. Xóa bảng health_profiles cũ
DROP TABLE IF EXISTS health_profiles CASCADE;

-- 4. Tạo bảng staff_profiles (Hồ sơ nhân viên)
CREATE TABLE IF NOT EXISTS staff_profiles (
    user_id            UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    staff_code         VARCHAR(30) UNIQUE NOT NULL,
    full_name          VARCHAR(150) NOT NULL,
    gender             VARCHAR(10),
    birth_date         DATE,
    specialization     VARCHAR(100),
    qualification      VARCHAR(100),
    employment_status  VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 5. Tạo bảng staff_permissions (Phân quyền nhân viên riêng biệt - 8 cờ nghiệp vụ + cờ permissions)
CREATE TABLE IF NOT EXISTS staff_permissions (
    user_id                UUID PRIMARY KEY REFERENCES staff_profiles(user_id) ON DELETE CASCADE,
    can_manage_users       BOOLEAN NOT NULL DEFAULT FALSE,
    can_manage_foods       BOOLEAN NOT NULL DEFAULT FALSE,
    can_manage_categories  BOOLEAN NOT NULL DEFAULT FALSE,
    can_review_documents   BOOLEAN NOT NULL DEFAULT FALSE,
    can_review_plans       BOOLEAN NOT NULL DEFAULT FALSE,
    can_review_ai_chat     BOOLEAN NOT NULL DEFAULT FALSE,
    can_review_logs        BOOLEAN NOT NULL DEFAULT FALSE,
    can_manage_permissions BOOLEAN NOT NULL DEFAULT FALSE,
    created_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 6. Cập nhật activity_logs
ALTER TABLE activity_logs ADD COLUMN IF NOT EXISTS started_at TIMESTAMPTZ;
ALTER TABLE activity_logs ADD COLUMN IF NOT EXISTS ended_at TIMESTAMPTZ;
ALTER TABLE activity_logs ADD COLUMN IF NOT EXISTS logged_at TIMESTAMPTZ DEFAULT now();
ALTER TABLE activity_logs DROP COLUMN IF EXISTS log_date;

-- 7. Recreate view v_daily_summary với user_info & activity_logs mới
CREATE OR REPLACE VIEW v_daily_summary AS
SELECT
    u.id AS user_id,
    d.day,
    COALESCE(m.kcal_in, 0)  AS kcal_intake,
    COALESCE(a.kcal_out, 0) AS kcal_burned,
    ui.daily_calorie_target,
    ui.daily_calorie_target - COALESCE(m.kcal_in, 0) + COALESCE(a.kcal_out, 0)
        AS kcal_remaining
FROM users u
CROSS JOIN LATERAL (
    SELECT generate_series(CURRENT_DATE - 30, CURRENT_DATE, '1 day')::date AS day
) d
LEFT JOIN user_info ui ON ui.user_id = u.id
LEFT JOIN LATERAL (
    SELECT SUM(calories_kcal) AS kcal_in FROM meal_logs ml
    WHERE ml.user_id = u.id AND ml.log_date = d.day
) m ON TRUE
LEFT JOIN LATERAL (
    SELECT SUM(calories_burned) AS kcal_out FROM activity_logs al
    WHERE al.user_id = u.id AND DATE(COALESCE(al.started_at, al.logged_at)) = d.day
) a ON TRUE;

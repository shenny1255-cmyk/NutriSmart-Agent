-- Migration 17: Xóa is_verified và tạo bảng staff_profiles cho EXPERT/ADMIN

-- 1. Xóa cột is_verified khỏi bảng users (đơn giản hóa theo góp ý của cô giáo)
ALTER TABLE users DROP COLUMN IF EXISTS is_verified;

-- 2. Tạo bảng mở rộng staff_profiles cho EXPERT / ADMIN
CREATE TABLE IF NOT EXISTS staff_profiles (
    user_id     UUID        PRIMARY KEY
                            REFERENCES users(id) ON DELETE CASCADE,
    staff_type  VARCHAR(20),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

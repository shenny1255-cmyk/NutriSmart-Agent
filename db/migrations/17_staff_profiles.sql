-- Migration 17: Xóa is_verified và tạo hồ sơ nhân viên cho EXPERT/ADMIN

-- 1. Xóa cột is_verified khỏi bảng users (đơn giản hóa theo góp ý của cô giáo)
ALTER TABLE users DROP COLUMN IF EXISTS is_verified;

-- 2. Tạo bảng mở rộng staff_profiles cho EXPERT / ADMIN
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

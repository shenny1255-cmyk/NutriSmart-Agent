-- Dữ liệu bệnh nền/dị ứng do người dùng tự khai báo, tách khỏi danh mục chuẩn.
ALTER TABLE user_info
    ADD COLUMN IF NOT EXISTS custom_conditions JSONB NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS custom_allergens JSONB NOT NULL DEFAULT '[]'::jsonb;

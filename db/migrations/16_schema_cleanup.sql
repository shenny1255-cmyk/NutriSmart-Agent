-- Migration 16: Lược bỏ các cột & bảng dư thừa trong CSDL theo thống nhất thiết kế
-- 1. Xóa parent_plan_id khỏi nutrition_plans (đã có user_id + version + created_at để xác định thứ tự)
ALTER TABLE nutrition_plans DROP COLUMN IF EXISTS parent_plan_id;

-- 2. Giữ cột bmi trong body_metrics_history (lưu mốc BMI lịch sử theo từng ngày cân)
ALTER TABLE body_metrics_history ADD COLUMN IF NOT EXISTS bmi NUMERIC(5, 2);

-- 3. Xóa country_code khỏi user_info (đã đơn giản hóa mặc định Việt Nam)
ALTER TABLE user_info DROP COLUMN IF EXISTS country_code;

-- 4. Xóa cột email_verified trùng lặp cũ trên users (dùng cột is_verified chuẩn)
ALTER TABLE users DROP COLUMN IF EXISTS email_verified;

-- 5. Thêm is_verified cho users (nếu CSDL cũ chưa có)
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_verified BOOLEAN NOT NULL DEFAULT false;

-- 6. Thêm status và status_note cho drugs (nếu CSDL cũ chưa có)
ALTER TABLE drugs ADD COLUMN IF NOT EXISTS status drug_status NOT NULL DEFAULT 'ALLOWED';
ALTER TABLE drugs ADD COLUMN IF NOT EXISTS status_note TEXT;

-- 7. Xóa 2 bảng dư thừa countries và drug_country_rules (đã gộp status & status_note vào thẳng bảng drugs)
DROP TABLE IF EXISTS drug_country_rules CASCADE;
DROP TABLE IF EXISTS countries CASCADE;

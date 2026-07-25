-- Xác minh email: cờ đánh dấu người dùng đã xác nhận địa chỉ email hay chưa.
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS email_verified BOOLEAN NOT NULL DEFAULT false;

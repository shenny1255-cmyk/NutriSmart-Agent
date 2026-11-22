-- Đăng nhập đơn thiết bị: mỗi lần đăng nhập tăng token_version, token cũ mang "tv" thấp hơn bị từ chối.
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS token_version INT NOT NULL DEFAULT 1;

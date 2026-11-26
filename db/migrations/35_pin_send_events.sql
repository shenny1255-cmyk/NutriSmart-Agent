-- Nhật ký gửi mã PIN đăng ký: giới hạn số lần gửi mỗi giờ theo email và theo IP để chống spam email.
-- Bản ghi cũ hơn 1 ngày được API tự dọn khi có yêu cầu gửi mã mới.
CREATE TABLE IF NOT EXISTS pin_send_events (
    id          BIGSERIAL    PRIMARY KEY,
    email       VARCHAR(255) NOT NULL,
    ip          VARCHAR(64)  NOT NULL,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_pin_send_events_email_time ON pin_send_events (email, created_at);
CREATE INDEX IF NOT EXISTS idx_pin_send_events_ip_time    ON pin_send_events (ip, created_at);

-- Nhật ký đồng ý xử lý dữ liệu cá nhân (Nghị định 13/2023/NĐ-CP) - kế hoạch ĐATN v2, GĐ1.
-- Chỉ THÊM, không sửa/xóa: mỗi lần đồng ý hoặc rút lại là một dòng mới, dòng mới nhất là
-- trạng thái hiện tại. Đây là bằng chứng "đồng ý được ghi nhận" khi cần đối chiếu.
CREATE TABLE IF NOT EXISTS user_consents (
    id            BIGSERIAL    PRIMARY KEY,
    user_id       UUID         NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    consent_type  VARCHAR(20)  NOT NULL CHECK (consent_type IN ('TERMS', 'HEALTH_DATA', 'CLOUD_AI')),
    granted       BOOLEAN      NOT NULL,
    version       VARCHAR(20)  NOT NULL,   -- phiên bản chính sách người dùng đã đọc
    source        VARCHAR(20)  NOT NULL,   -- REGISTER | PROFILE
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_user_consents_user_type
    ON user_consents (user_id, consent_type, created_at DESC);

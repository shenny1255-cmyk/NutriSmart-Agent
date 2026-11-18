-- Nhật ký khẩu phần từ ảnh (kế hoạch ĐATN v2, mục 2.1 và 2.3 - GĐ3).
-- Lưu dự đoán của AI và số người dùng chốt để đo sai số, làm đầu vào cho Expert duyệt ca sửa.
-- KHÔNG lưu ảnh món ăn.
CREATE TABLE IF NOT EXISTS vision_feedback (
    id                   UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id              UUID          NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    food_name            VARCHAR(200)  NOT NULL,
    ai_total_kcal        NUMERIC(8, 2),             -- tổng AI tự đoán (mốc "trước")
    predicted_kcal       NUMERIC(8, 2) NOT NULL,    -- gram AI x bảng thành phần (mốc "sau")
    final_kcal           NUMERIC(8, 2),             -- sau khi người dùng chốt
    predicted_components JSONB         NOT NULL,
    final_components     JSONB,
    status               VARCHAR(20)   NOT NULL DEFAULT 'PREDICTED'
                         CHECK (status IN ('PREDICTED', 'CONFIRMED', 'CORRECTED')),
    review_status        VARCHAR(20)   NOT NULL DEFAULT 'PENDING'
                         CHECK (review_status IN ('PENDING', 'APPROVED', 'REJECTED')),
    meal_log_id          BIGINT        REFERENCES meal_logs(id) ON DELETE SET NULL,
    created_at           TIMESTAMPTZ   NOT NULL DEFAULT now(),
    confirmed_at         TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_vision_feedback_review
    ON vision_feedback (status, review_status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_vision_feedback_user
    ON vision_feedback (user_id, created_at DESC);

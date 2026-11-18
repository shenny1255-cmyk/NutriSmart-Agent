-- Expert duyệt ca sửa khẩu phần và kho few-shot (kế hoạch ĐATN v2, mục 2.1 - GĐ3).
-- Chỉ ca do Expert duyệt mới vào kho. Kho chỉ giữ tên món, tên thành phần và gram: không có
-- user_id, không có ảnh, nên ví dụ không gắn với người đã gửi ca sửa.
ALTER TABLE vision_feedback
    ADD COLUMN IF NOT EXISTS reviewed_by  UUID REFERENCES users(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS reviewed_at  TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS review_note  TEXT,
    ADD COLUMN IF NOT EXISTS few_shot_ids JSONB NOT NULL DEFAULT '[]'::jsonb;  -- ví dụ đã dùng khi dự đoán

CREATE TABLE IF NOT EXISTS few_shot_examples (
    id           UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    feedback_id  UUID          UNIQUE REFERENCES vision_feedback(id) ON DELETE SET NULL,
    food_name    VARCHAR(200)  NOT NULL,
    components   JSONB         NOT NULL,
    total_kcal   NUMERIC(8, 2) NOT NULL,
    embedding    vector(1024),                  -- NULL khi Ollama tắt lúc duyệt, vẫn tìm được bằng trigram
    is_active    BOOLEAN       NOT NULL DEFAULT TRUE,
    approved_by  UUID          REFERENCES users(id) ON DELETE SET NULL,
    created_at   TIMESTAMPTZ   NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_few_shot_name_trgm
    ON few_shot_examples USING gin (f_unaccent(lower(food_name)) gin_trgm_ops) WHERE is_active;
CREATE INDEX IF NOT EXISTS idx_few_shot_embedding
    ON few_shot_examples USING hnsw (embedding vector_cosine_ops) WHERE is_active AND embedding IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_vision_feedback_queue
    ON vision_feedback (created_at) WHERE status = 'CORRECTED' AND review_status = 'PENDING';

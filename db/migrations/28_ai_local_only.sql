-- GĐ1 ĐATN - quyền riêng tư: người dùng có thể yêu cầu chỉ xử lý dữ liệu bằng AI nội bộ (Ollama).
-- Khi bật, AI Provider Adapter (services/llm.py) không gửi dữ liệu của người này ra cloud.
ALTER TABLE user_profile
    ADD COLUMN IF NOT EXISTS ai_local_only BOOLEAN NOT NULL DEFAULT FALSE;

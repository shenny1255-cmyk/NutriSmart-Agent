-- Vector search: HNSW + cosine
CREATE INDEX idx_chunks_embedding ON doc_chunks
    USING hnsw (embedding vector_cosine_ops);

-- Keyword search: GIN + trigram  → kết hợp 2 cái này ra HYBRID SEARCH
CREATE INDEX idx_chunks_content_trgm ON doc_chunks
    USING gin (content gin_trgm_ops);

CREATE INDEX idx_foods_name_trgm ON foods USING gin (name gin_trgm_ops);

-- Index thường
CREATE INDEX idx_users_role       ON users(role) WHERE deleted_at IS NULL;
CREATE INDEX idx_documents_status ON documents(status);
CREATE INDEX idx_meal_logs_user   ON meal_logs(user_id, log_date);
CREATE INDEX idx_activity_user    ON activity_logs(user_id, log_date);
CREATE INDEX idx_plans_active     ON nutrition_plans(user_id) WHERE status = 'ACTIVE';
CREATE INDEX idx_notif_unread     ON notifications(user_id) WHERE is_read = FALSE;
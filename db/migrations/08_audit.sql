CREATE TABLE notifications (
    id         BIGSERIAL PRIMARY KEY,
    user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type       VARCHAR(50) NOT NULL,   -- REMINDER / PLAN_ALERT / SYSTEM
    title      VARCHAR(200) NOT NULL,
    body       TEXT,
    is_read    BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE audit_logs (
    id          BIGSERIAL PRIMARY KEY,
    actor_id    UUID REFERENCES users(id),
    action      VARCHAR(50) NOT NULL,   -- CREATE/UPDATE/DELETE/APPROVE
    entity      VARCHAR(80) NOT NULL,   -- 'drugs', 'documents'
    entity_id   TEXT,
    before_data JSONB,
    after_data  JSONB,
    ip_address  INET,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
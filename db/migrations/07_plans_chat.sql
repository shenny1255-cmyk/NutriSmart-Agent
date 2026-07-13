CREATE TABLE nutrition_plans (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id           UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    version           INT NOT NULL DEFAULT 1,
    parent_plan_id    UUID REFERENCES nutrition_plans(id),  -- hiệu chỉnh từ plan nào
    start_date        DATE NOT NULL,
    end_date          DATE NOT NULL,
    daily_kcal_target INT NOT NULL,
    goal              goal_enum NOT NULL,
    content           JSONB NOT NULL,      -- thực đơn + lịch tập do LLM sinh
    generated_by      VARCHAR(100),        -- tên model
    status            plan_status NOT NULL DEFAULT 'ACTIVE',
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (end_date >= start_date)
);

CREATE TABLE plan_evaluations (
    id               BIGSERIAL PRIMARY KEY,
    plan_id          UUID NOT NULL REFERENCES nutrition_plans(id) ON DELETE CASCADE,
    period_start     DATE NOT NULL,
    period_end       DATE NOT NULL,
    avg_kcal_intake  NUMERIC(8,2),
    weight_change_kg NUMERIC(5,2),
    result           eval_result NOT NULL,
    ai_feedback      TEXT,
    evaluated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE chat_sessions (
    id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title      VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE chat_messages (
    id         BIGSERIAL PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role       VARCHAR(20) NOT NULL CHECK (role IN ('user','assistant','system')),
    content    TEXT NOT NULL,
    flagged    BOOLEAN NOT NULL DEFAULT FALSE,  -- chuyên gia gắn cờ sai lệch
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE message_citations (
    message_id BIGINT REFERENCES chat_messages(id) ON DELETE CASCADE,
    chunk_id   BIGINT REFERENCES doc_chunks(id) ON DELETE CASCADE,
    score      NUMERIC(5,4),
    rank       SMALLINT,
    PRIMARY KEY (message_id, chunk_id)
);
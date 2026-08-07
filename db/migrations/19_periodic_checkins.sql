-- Check-in tiến độ định kỳ 14 ngày.
-- Trạng thái DUE/OVERDUE được suy ra theo ngày, không lưu trực tiếp.

-- Một số volume dev cũ được tạo trước khi parent_plan_id có trong migration 07.
ALTER TABLE nutrition_plans
    ADD COLUMN IF NOT EXISTS parent_plan_id UUID REFERENCES nutrition_plans(id);

-- Dọn dữ liệu ACTIVE trùng trước khi khóa invariant một plan ACTIVE/user.
WITH ranked_active AS (
    SELECT id, ROW_NUMBER() OVER (
        PARTITION BY user_id ORDER BY version DESC, created_at DESC, id DESC
    ) AS rn
    FROM nutrition_plans
    WHERE status = 'ACTIVE'
)
UPDATE nutrition_plans p
SET status = 'REVISED'
FROM ranked_active r
WHERE p.id = r.id AND r.rn > 1;

DROP INDEX IF EXISTS idx_plans_active;
CREATE UNIQUE INDEX uq_active_plan_per_user
    ON nutrition_plans(user_id) WHERE status = 'ACTIVE';

CREATE TABLE plan_checkin_series (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    goal        goal_enum NOT NULL,
    status      VARCHAR(20) NOT NULL DEFAULT 'ACTIVE'
                CHECK (status IN ('ACTIVE', 'CLOSED')),
    started_at  DATE NOT NULL,
    closed_at   DATE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (closed_at IS NULL OR closed_at >= started_at)
);

CREATE UNIQUE INDEX uq_active_checkin_series_per_user
    ON plan_checkin_series(user_id) WHERE status = 'ACTIVE';

CREATE TABLE plan_checkins (
    id                         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    series_id                  UUID NOT NULL REFERENCES plan_checkin_series(id) ON DELETE CASCADE,
    user_id                    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    plan_id                    UUID NOT NULL REFERENCES nutrition_plans(id) ON DELETE CASCADE,
    adjusted_plan_id           UUID REFERENCES nutrition_plans(id) ON DELETE SET NULL,
    previous_checkin_id        UUID REFERENCES plan_checkins(id) ON DELETE SET NULL,
    period_number              INT NOT NULL CHECK (period_number > 0),
    start_date                 DATE NOT NULL,
    period_end                 DATE NOT NULL,
    due_date                   DATE NOT NULL,
    grace_until                DATE NOT NULL,

    baseline_weight_kg         NUMERIC(5,2) NOT NULL CHECK (baseline_weight_kg BETWEEN 20 AND 300),
    baseline_waist_cm          NUMERIC(5,2),
    goal_snapshot              goal_enum NOT NULL,
    target_kcal_snapshot       INT NOT NULL CHECK (target_kcal_snapshot BETWEEN 1200 AND 4000),
    activity_target_snapshot   SMALLINT CHECK (activity_target_snapshot BETWEEN 1 AND 5),
    expected_weight_min_kg     NUMERIC(5,2) NOT NULL,
    expected_weight_max_kg     NUMERIC(5,2) NOT NULL,
    prediction_rule_version    VARCHAR(30) NOT NULL,

    actual_weight_kg           NUMERIC(5,2) CHECK (actual_weight_kg BETWEEN 20 AND 300),
    actual_waist_cm            NUMERIC(5,2),
    actual_activity_level      SMALLINT CHECK (actual_activity_level BETWEEN 1 AND 5),
    adherence_pct              SMALLINT CHECK (adherence_pct BETWEEN 0 AND 100),
    energy_level               SMALLINT CHECK (energy_level BETWEEN 1 AND 5),
    hunger_level               SMALLINT CHECK (hunger_level BETWEEN 1 AND 5),
    sleep_quality              SMALLINT CHECK (sleep_quality BETWEEN 1 AND 5),
    notes                      VARCHAR(1000),

    meal_log_days              SMALLINT,
    avg_kcal_intake            NUMERIC(8,2),
    weight_change_kg           NUMERIC(5,2),
    data_quality_result        VARCHAR(30),
    adherence_result           VARCHAR(20),
    outcome_result             VARCHAR(30),
    safety_flags               JSONB NOT NULL DEFAULT '[]'::jsonb,
    recommendation             VARCHAR(30),
    recommendation_reason      TEXT,
    proposed_kcal_target       INT,

    ai_feedback                TEXT,
    feedback_status            VARCHAR(20) NOT NULL DEFAULT 'NOT_REQUESTED'
                               CHECK (feedback_status IN ('NOT_REQUESTED', 'PENDING', 'COMPLETED', 'FAILED')),
    status                     VARCHAR(20) NOT NULL DEFAULT 'OPEN'
                               CHECK (status IN ('OPEN', 'COMPLETED', 'MISSED', 'CANCELLED')),
    decision                   VARCHAR(30) CHECK (decision IN ('CONTINUE', 'APPLY_ADJUSTMENT')),
    submitted_at               TIMESTAMPTZ,
    completed_at               TIMESTAMPTZ,
    decision_at                TIMESTAMPTZ,
    adjustment_applied_at      TIMESTAMPTZ,
    created_at                 TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                 TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (series_id, period_number),
    CHECK (period_end = start_date + 13),
    CHECK (due_date = start_date + 14),
    CHECK (grace_until >= due_date),
    CHECK (expected_weight_min_kg <= expected_weight_max_kg),
    CHECK (actual_waist_cm IS NULL OR actual_waist_cm BETWEEN 30 AND 250),
    CHECK (baseline_waist_cm IS NULL OR baseline_waist_cm BETWEEN 30 AND 250),
    CHECK (proposed_kcal_target IS NULL OR proposed_kcal_target BETWEEN 1200 AND 4000)
);

CREATE UNIQUE INDEX uq_open_checkin_per_user
    ON plan_checkins(user_id) WHERE status = 'OPEN';
CREATE INDEX ix_plan_checkins_user_due ON plan_checkins(user_id, due_date DESC);
CREATE INDEX ix_plan_checkins_feedback ON plan_checkins(feedback_status)
    WHERE feedback_status = 'PENDING';

-- Khóa chống tạo thông báo trùng khi job chạy lại.
ALTER TABLE notifications ADD COLUMN IF NOT EXISTS dedupe_key VARCHAR(150);
CREATE UNIQUE INDEX IF NOT EXISTS uq_notifications_dedupe_key
    ON notifications(dedupe_key) WHERE dedupe_key IS NOT NULL;

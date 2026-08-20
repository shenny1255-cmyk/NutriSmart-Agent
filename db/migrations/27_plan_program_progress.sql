-- Chương trình dài hạn, tiến độ ngày và nguồn nhật ký từ lộ trình.

ALTER TABLE plan_checkin_series
    ADD COLUMN IF NOT EXISTS duration_months SMALLINT,
    ADD COLUMN IF NOT EXISTS planned_end_date DATE,
    ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS completion_reason VARCHAR(30);

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM plan_checkin_series s
        LEFT JOIN plan_checkins c ON c.series_id = s.id
        GROUP BY s.id, s.started_at
        HAVING GREATEST(
            3,
            CEIL((COALESCE(MAX(c.period_end), s.started_at + 83) - s.started_at + 1) / 28.0)::INT
        ) > 12
    ) THEN
        RAISE EXCEPTION 'Có chương trình cũ dài hơn 12 tháng, cần rà soát thủ công';
    END IF;
END $$;

WITH coverage AS (
    SELECT s.id,
           GREATEST(
               3,
               CEIL((COALESCE(MAX(c.period_end), s.started_at + 83) - s.started_at + 1) / 28.0)::INT
           ) AS needed_months
    FROM plan_checkin_series s
    LEFT JOIN plan_checkins c ON c.series_id = s.id
    GROUP BY s.id, s.started_at
)
UPDATE plan_checkin_series s
SET duration_months = coverage.needed_months,
    planned_end_date = s.started_at + coverage.needed_months * 28 - 1
FROM coverage
WHERE coverage.id = s.id
  AND (s.duration_months IS NULL OR s.planned_end_date IS NULL);

ALTER TABLE plan_checkin_series
    ALTER COLUMN duration_months SET DEFAULT 3,
    ALTER COLUMN duration_months SET NOT NULL,
    ALTER COLUMN planned_end_date SET NOT NULL;

ALTER TABLE plan_checkin_series
    DROP CONSTRAINT IF EXISTS plan_checkin_series_status_check,
    ADD CONSTRAINT plan_checkin_series_status_check
        CHECK (status IN ('ACTIVE', 'CLOSED', 'COMPLETED')),
    ADD CONSTRAINT plan_checkin_series_duration_check
        CHECK (duration_months BETWEEN 1 AND 12),
    ADD CONSTRAINT plan_checkin_series_end_check
        CHECK (planned_end_date >= started_at);

CREATE TABLE IF NOT EXISTS plan_daily_progress (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    series_id           UUID NOT NULL REFERENCES plan_checkin_series(id) ON DELETE CASCADE,
    checkin_id          UUID NOT NULL REFERENCES plan_checkins(id) ON DELETE CASCADE,
    plan_id             UUID NOT NULL REFERENCES nutrition_plans(id) ON DELETE CASCADE,
    progress_date       DATE NOT NULL,
    template_day_index  SMALLINT NOT NULL CHECK (template_day_index BETWEEN 0 AND 6),
    checked_items       JSONB NOT NULL DEFAULT '[]'::jsonb,
    status              VARCHAR(20) NOT NULL DEFAULT 'IN_PROGRESS'
                        CHECK (status IN ('IN_PROGRESS', 'COMPLETED')),
    completed_at        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (checkin_id, progress_date),
    CHECK (jsonb_typeof(checked_items) = 'array')
);

ALTER TABLE meal_logs
    ADD COLUMN IF NOT EXISTS source_type VARCHAR(20),
    ADD COLUMN IF NOT EXISTS source_progress_id UUID REFERENCES plan_daily_progress(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS source_item_key VARCHAR(30),
    ADD COLUMN IF NOT EXISTS item_name_snapshot VARCHAR(200);

ALTER TABLE activity_logs
    ADD COLUMN IF NOT EXISTS source_type VARCHAR(20),
    ADD COLUMN IF NOT EXISTS source_progress_id UUID REFERENCES plan_daily_progress(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS source_item_key VARCHAR(30),
    ADD COLUMN IF NOT EXISTS item_name_snapshot VARCHAR(200);

CREATE UNIQUE INDEX IF NOT EXISTS uq_plan_meal_log_item
    ON meal_logs(source_progress_id, source_item_key)
    WHERE source_type = 'PLAN';

CREATE UNIQUE INDEX IF NOT EXISTS uq_plan_activity_log_item
    ON activity_logs(source_progress_id, source_item_key)
    WHERE source_type = 'PLAN';

CREATE INDEX IF NOT EXISTS ix_plan_daily_progress_user_date
    ON plan_daily_progress(user_id, progress_date DESC);

-- Migration 19 đã tạo các index unique này; giữ lệnh idempotent cho database cũ.
DROP INDEX IF EXISTS idx_plans_active;
CREATE UNIQUE INDEX IF NOT EXISTS uq_active_plan_per_user
    ON nutrition_plans(user_id) WHERE status = 'ACTIVE';
CREATE UNIQUE INDEX IF NOT EXISTS uq_active_checkin_series_per_user
    ON plan_checkin_series(user_id) WHERE status = 'ACTIVE';

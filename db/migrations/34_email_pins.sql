CREATE TABLE IF NOT EXISTS email_pins (
    email       VARCHAR(255) PRIMARY KEY,
    pin_hash    VARCHAR(255) NOT NULL,
    attempts    INT NOT NULL DEFAULT 0,
    expires_at  TIMESTAMPTZ NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

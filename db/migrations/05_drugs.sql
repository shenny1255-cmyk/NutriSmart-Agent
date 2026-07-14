CREATE TABLE drug_categories (
    id   SERIAL PRIMARY KEY,
    name VARCHAR(150) UNIQUE NOT NULL
);

CREATE TABLE drugs (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    category_id       INT REFERENCES drug_categories(id) ON DELETE SET NULL,
    name              VARCHAR(200) NOT NULL,
    active_ingredient VARCHAR(200),
    indications       TEXT,
    side_effects      TEXT,
    contraindications TEXT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE drug_country_rules (
    drug_id      UUID    REFERENCES drugs(id) ON DELETE CASCADE,
    country_code CHAR(2) REFERENCES countries(code) ON DELETE CASCADE,
    status       drug_status NOT NULL DEFAULT 'ALLOWED',
    note         TEXT,
    updated_by   UUID REFERENCES users(id),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (drug_id, country_code)
);
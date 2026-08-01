CREATE TABLE drug_categories (
    id   SERIAL PRIMARY KEY,
    name VARCHAR(150) UNIQUE NOT NULL
);

CREATE TABLE drugs (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    category_id       INT REFERENCES drug_categories(id) ON DELETE SET NULL,
    document_id       UUID REFERENCES documents(id) ON DELETE SET NULL,
    name              VARCHAR(200) NOT NULL,
    active_ingredient VARCHAR(200),
    indications       TEXT,
    side_effects      TEXT,
    contraindications TEXT,
    status            drug_status NOT NULL DEFAULT 'ALLOWED',
    status_note       TEXT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at        TIMESTAMPTZ
);
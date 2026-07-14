CREATE TABLE doc_categories (
    id        SERIAL PRIMARY KEY,
    parent_id INT REFERENCES doc_categories(id) ON DELETE SET NULL,  -- cây danh mục
    name      VARCHAR(150) NOT NULL,
    slug      VARCHAR(150) UNIQUE NOT NULL
);

CREATE TABLE documents (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    category_id INT REFERENCES doc_categories(id) ON DELETE SET NULL,
    title       TEXT NOT NULL,
    source_url  TEXT,                    -- pubmed / WHO / MOH / USDA
    source_name VARCHAR(150),
    language    VARCHAR(10) DEFAULT 'vi',
    file_path   TEXT,                    -- key trong object storage
    raw_text    TEXT,                    -- kết quả sau OCR
    status      doc_status NOT NULL DEFAULT 'PENDING',  -- luồng duyệt của EXPERT
    uploaded_by UUID REFERENCES users(id),
    approved_by UUID REFERENCES users(id),
    approved_at TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE doc_chunks (
    id          BIGSERIAL PRIMARY KEY,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INT NOT NULL,
    content     TEXT NOT NULL,
    token_count INT,
    embedding   vector(1024),            -- BGE-M3 = 1024 chiều
    metadata    JSONB DEFAULT '{}'::jsonb,
    UNIQUE (document_id, chunk_index)
);
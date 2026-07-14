CREATE TABLE foods (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name          VARCHAR(200) NOT NULL,
    serving_desc  VARCHAR(100),          -- "1 tô", "100g"
    serving_gram  NUMERIC(7,2),
    calories_kcal NUMERIC(7,2) NOT NULL,
    protein_g     NUMERIC(6,2) DEFAULT 0,
    carb_g        NUMERIC(6,2) DEFAULT 0,
    fat_g         NUMERIC(6,2) DEFAULT 0,
    source        VARCHAR(100)           -- 'USDA FDC' / 'Tự nhập'
);

CREATE TABLE meal_images (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id           UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    image_path        TEXT NOT NULL,
    status            job_status NOT NULL DEFAULT 'QUEUED',
    predicted_food_id UUID REFERENCES foods(id),
    confidence        NUMERIC(4,3),
    raw_prediction    JSONB,             -- lưu top-k dự đoán của CNN
    estimated_kcal    NUMERIC(7,2),
    suitability_note  TEXT,              -- đánh giá phù hợp với bệnh nền
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE meal_logs (
    id            BIGSERIAL PRIMARY KEY,
    user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    food_id       UUID REFERENCES foods(id),
    meal_image_id UUID REFERENCES meal_images(id),
    meal_type     meal_type NOT NULL,
    quantity      NUMERIC(6,2) NOT NULL DEFAULT 1,
    calories_kcal NUMERIC(7,2) NOT NULL,   -- SNAPSHOT
    logged_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    log_date      DATE NOT NULL DEFAULT CURRENT_DATE
);

CREATE TABLE exercises (
    id        SERIAL PRIMARY KEY,
    name      VARCHAR(150) NOT NULL,
    met_value NUMERIC(4,2),      -- hệ số MET để tính calo đốt
    category  VARCHAR(80)
);

CREATE TABLE activity_logs (
    id              BIGSERIAL PRIMARY KEY,
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    exercise_id     INT REFERENCES exercises(id),
    steps           INT DEFAULT 0,
    duration_min    INT DEFAULT 0,
    calories_burned NUMERIC(7,2) DEFAULT 0,
    log_date        DATE NOT NULL DEFAULT CURRENT_DATE
);
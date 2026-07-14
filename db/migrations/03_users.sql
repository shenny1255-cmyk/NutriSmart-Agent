CREATE TABLE countries (
    code CHAR(2) PRIMARY KEY,
    name VARCHAR(100) NOT NULL
);

CREATE TABLE users (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email         VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name     VARCHAR(150),
    role          user_role NOT NULL DEFAULT 'USER',
    country_code  CHAR(2) REFERENCES countries(code),
    is_active     BOOLEAN NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at    TIMESTAMPTZ          -- soft delete
);

CREATE TABLE health_profiles (
    id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id        UUID UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    gender         gender_enum,
    birth_date     DATE,
    height_cm      NUMERIC(5,2) CHECK (height_cm > 0),
    weight_kg      NUMERIC(5,2) CHECK (weight_kg > 0),
    bmi            NUMERIC(5,2) GENERATED ALWAYS AS
                     (weight_kg / ((height_cm/100) * (height_cm/100))) STORED,
    activity_level SMALLINT CHECK (activity_level BETWEEN 1 AND 5),
    goal           goal_enum NOT NULL DEFAULT 'MAINTAIN',
    daily_calorie_target INT,
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE medical_conditions (
    id   SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,   -- ICD-10
    name VARCHAR(150) NOT NULL
);

CREATE TABLE allergens (
    id   SERIAL PRIMARY KEY,
    name VARCHAR(150) UNIQUE NOT NULL
);

CREATE TABLE profile_conditions (
    profile_id   UUID REFERENCES health_profiles(id) ON DELETE CASCADE,
    condition_id INT  REFERENCES medical_conditions(id) ON DELETE CASCADE,
    PRIMARY KEY (profile_id, condition_id)      -- khóa chính kép
);

CREATE TABLE profile_allergens (
    profile_id  UUID REFERENCES health_profiles(id) ON DELETE CASCADE,
    allergen_id INT  REFERENCES allergens(id) ON DELETE CASCADE,
    severity    SMALLINT CHECK (severity BETWEEN 1 AND 3),
    PRIMARY KEY (profile_id, allergen_id)
);
CREATE TABLE body_metrics_history (
    id          BIGSERIAL PRIMARY KEY,
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    recorded_at DATE NOT NULL DEFAULT CURRENT_DATE,
    weight_kg   NUMERIC(5,2),
    bmi         NUMERIC(5,2),
    UNIQUE (user_id, recorded_at)      -- mỗi ngày 1 bản ghi
);
-- Danh mục mức độ vận động; id 1-5 được cố định để tương thích API hiện tại.
CREATE TABLE IF NOT EXISTS activity_levels (
    id                 SMALLINT PRIMARY KEY CHECK (id BETWEEN 1 AND 5),
    name               VARCHAR(100) UNIQUE NOT NULL,
    description        VARCHAR(500),
    calorie_multiplier NUMERIC(4, 3) NOT NULL CHECK (calorie_multiplier > 0)
);

INSERT INTO activity_levels (id, name, description, calorie_multiplier) VALUES
    (1, 'Ít vận động',       'Hầu như không tập thể dục',                       1.200),
    (2, 'Vận động nhẹ',      'Tập nhẹ từ 1 đến 3 ngày mỗi tuần',                1.375),
    (3, 'Vận động vừa',      'Tập vừa từ 3 đến 5 ngày mỗi tuần',                1.550),
    (4, 'Vận động nhiều',    'Tập nặng từ 6 đến 7 ngày mỗi tuần',               1.725),
    (5, 'Vận động rất nhiều','Tập rất nặng hoặc lao động thể lực thường xuyên', 1.900)
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    calorie_multiplier = EXCLUDED.calorie_multiplier;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'user_info' AND column_name = 'activity_level'
    ) THEN
        ALTER TABLE user_info RENAME COLUMN activity_level TO activity_level_id;
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'user_info_activity_level_id_fkey'
    ) THEN
        ALTER TABLE user_info
            ADD CONSTRAINT user_info_activity_level_id_fkey
            FOREIGN KEY (activity_level_id) REFERENCES activity_levels(id);
    END IF;
END $$;

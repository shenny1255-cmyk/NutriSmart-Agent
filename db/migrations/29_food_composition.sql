-- Bảng thành phần thực phẩm Việt Nam (Viện Dinh dưỡng, NXB Y học 2007) - kế hoạch ĐATN v2, GĐ1.
-- Giá trị cho 100 g PHẦN ĂN ĐƯỢC. Nguồn sự thật cho kcal/macro: LLM chỉ ước lượng gram,
-- kcal tra từ bảng này (dùng cho Vision bóc tách thành phần ở GĐ3).
-- Dữ liệu nằm ở backend/data/food_composition_vn2007.csv (nhóm duyệt qua PR); backend tự nạp
-- khi bảng rỗng, hoặc chạy tay: python scripts/load_food_composition.py
CREATE TABLE IF NOT EXISTS food_composition (
    code            VARCHAR(10)  PRIMARY KEY,          -- mã số trong Bảng TPTP 2007
    name_vi         VARCHAR(200) NOT NULL,
    name_en         VARCHAR(200),
    food_group      VARCHAR(100),
    waste_pct       NUMERIC(5, 1),                     -- % thải bỏ (vỏ, xương...)
    energy_kcal     NUMERIC(7, 1) NOT NULL,
    protein_g       NUMERIC(6, 2),
    fat_g           NUMERIC(6, 2),
    carb_g          NUMERIC(6, 2),
    fiber_g         NUMERIC(6, 2),
    sugar_g         NUMERIC(6, 2),
    water_g         NUMERIC(6, 2),
    sodium_mg       NUMERIC(8, 1),
    cholesterol_mg  NUMERIC(8, 1),
    purine_mg       NUMERIC(8, 1),
    book_page       SMALLINT,
    source          VARCHAR(255) NOT NULL,
    check_note      TEXT,                              -- ghi chú tự động khi trích xuất (Atwater lệch, số mơ hồ)
    review_status   VARCHAR(20)  NOT NULL DEFAULT 'CHUA_DUYET',  -- CHUA_DUYET | DA_DUYET | CAN_SUA
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_food_composition_name_unaccent_trgm
    ON food_composition USING gin (f_unaccent(lower(name_vi)) gin_trgm_ops);

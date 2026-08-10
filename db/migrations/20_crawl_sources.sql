-- Migration 20: Quản lý nguồn cào dữ liệu y tế động (Dynamic Crawl Sources)

CREATE TABLE IF NOT EXISTS crawl_sources (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name        VARCHAR(255) NOT NULL,
    source_key  VARCHAR(100) NOT NULL UNIQUE,
    domain      VARCHAR(255) NOT NULL,
    base_urls   JSONB NOT NULL DEFAULT '[]'::jsonb,
    is_active   BOOLEAN NOT NULL DEFAULT true,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_crawl_sources_active ON crawl_sources(is_active) WHERE is_active = true;

-- Seed dữ liệu mẫu cho Bộ Y tế và Vinmec
INSERT INTO crawl_sources (name, source_key, domain, base_urls)
VALUES
(
    'Báo Sức khỏe & Đời sống - Bộ Y tế',
    'moh',
    'suckhoedoisong.vn',
    '[
        "https://suckhoedoisong.vn/che-do-an-trong-benh-dai-thao-duong-169240302134740875.htm",
        "https://suckhoedoisong.vn/che-do-an-cho-nguoi-benh-tieu-duong-type-2-169241027095715726.htm",
        "https://suckhoedoisong.vn/goi-y-thuc-don-1-tuan-cho-benh-nhan-dai-thao-duong-type-2-169220126162210889.htm",
        "https://suckhoedoisong.vn/9-thuc-pham-nguoi-benh-gout-nen-dua-vao-thuc-don-hang-ngay-169221227223435435.htm",
        "https://suckhoedoisong.vn/thuc-pham-nao-co-purine-thap-an-toan-cho-nguoi-benh-gout-169231210143003179.htm",
        "https://suckhoedoisong.vn/che-do-an-uong-khi-mac-benh-roi-loan-lipid-mau-169240506000646732.htm"
    ]'::jsonb
),
(
    'Hệ thống Y tế Vinmec',
    'vinmec',
    'vinmec.com',
    '[
        "https://www.vinmec.com/vie/bai-viet/che-do-an-cho-nguoi-benh-gout-vi",
        "https://www.vinmec.com/vie/bai-viet/che-do-cho-nguoi-benh-tang-huyet-ap-vi",
        "https://www.vinmec.com/vie/bai-viet/tim-hieu-ve-che-do-dash-cho-benh-nhan-tang-huyet-ap-vi",
        "https://www.vinmec.com/vie/bai-viet/dinh-duong-trong-benh-roi-loan-lipid-mau-vi"
    ]'::jsonb
)
ON CONFLICT (source_key) DO NOTHING;

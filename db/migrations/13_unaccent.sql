-- Bỏ dấu tiếng Việt khi tìm kiếm: gõ "nguyen van an" vẫn ra "Nguyễn Văn An".
-- Dùng ở màn Quản lý người dùng (tìm theo họ tên hoặc email).
CREATE EXTENSION IF NOT EXISTS unaccent;

-- Index trgm trên tên đã bỏ dấu → tìm theo tên vẫn nhanh khi bảng users lớn.
-- unaccent() không IMMUTABLE nên phải bọc qua một hàm wrapper mới đánh index được.
CREATE OR REPLACE FUNCTION f_unaccent(text)
RETURNS text
LANGUAGE sql IMMUTABLE PARALLEL SAFE STRICT
AS $$ SELECT public.unaccent('public.unaccent', $1) $$;

CREATE INDEX IF NOT EXISTS idx_user_info_full_name_unaccent_trgm
    ON user_info USING gin (f_unaccent(coalesce(full_name, '')) gin_trgm_ops);

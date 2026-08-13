-- Đặt tên bảng liên kết theo thực thể đang được tham chiếu và bỏ cột không dùng.
DO $$
BEGIN
    IF to_regclass('public.profile_conditions') IS NOT NULL
       AND to_regclass('public.user_medical_conditions') IS NULL THEN
        ALTER TABLE profile_conditions RENAME TO user_medical_conditions;
    END IF;

    IF to_regclass('public.profile_allergens') IS NOT NULL
       AND to_regclass('public.user_allergens') IS NULL THEN
        ALTER TABLE profile_allergens RENAME TO user_allergens;
    END IF;
END $$;

ALTER TABLE user_allergens DROP COLUMN IF EXISTS severity;

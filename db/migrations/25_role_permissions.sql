-- Chuyển phân quyền riêng từng nhân viên sang bộ quyền dùng chung theo vai trò.
CREATE TABLE IF NOT EXISTS role_permissions (
    role                       user_role PRIMARY KEY,
    can_manage_users           BOOLEAN NOT NULL DEFAULT FALSE,
    can_manage_foods           BOOLEAN NOT NULL DEFAULT FALSE,
    can_manage_categories      BOOLEAN NOT NULL DEFAULT FALSE,
    can_review_documents       BOOLEAN NOT NULL DEFAULT FALSE,
    can_review_plans           BOOLEAN NOT NULL DEFAULT FALSE,
    can_review_ai_chat         BOOLEAN NOT NULL DEFAULT FALSE,
    can_review_logs            BOOLEAN NOT NULL DEFAULT FALSE,
    can_manage_permissions     BOOLEAN NOT NULL DEFAULT FALSE,
    created_at                 TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                 TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO role_permissions (
    role, can_manage_users, can_manage_foods, can_manage_categories,
    can_review_documents, can_review_plans, can_review_ai_chat,
    can_review_logs, can_manage_permissions
) VALUES
    ('USER',   FALSE, FALSE, FALSE, FALSE, FALSE, FALSE, FALSE, FALSE),
    ('EXPERT', FALSE, FALSE, FALSE, TRUE,  TRUE,  TRUE,  TRUE,  FALSE),
    ('ADMIN',  TRUE,  TRUE,  TRUE,  TRUE,  TRUE,  TRUE,  TRUE,  TRUE)
ON CONFLICT (role) DO NOTHING;

-- Nếu dữ liệu cũ có tùy chỉnh, quyền nào từng được cấp cho ít nhất một nhân viên
-- của vai trò đó sẽ được giữ lại cho cả vai trò.
DO $$
BEGIN
    IF to_regclass('public.staff_permissions') IS NOT NULL THEN
        INSERT INTO role_permissions (
            role, can_manage_users, can_manage_foods, can_manage_categories,
            can_review_documents, can_review_plans, can_review_ai_chat,
            can_review_logs, can_manage_permissions
        )
        SELECT
            u.role,
            BOOL_OR(sp.can_manage_users), BOOL_OR(sp.can_manage_foods),
            BOOL_OR(sp.can_manage_categories), BOOL_OR(sp.can_review_documents),
            BOOL_OR(sp.can_review_plans), BOOL_OR(sp.can_review_ai_chat),
            BOOL_OR(sp.can_review_logs), BOOL_OR(sp.can_manage_permissions)
        FROM staff_permissions sp
        JOIN users u ON u.id = sp.user_id
        GROUP BY u.role
        ON CONFLICT (role) DO UPDATE SET
            can_manage_users = EXCLUDED.can_manage_users,
            can_manage_foods = EXCLUDED.can_manage_foods,
            can_manage_categories = EXCLUDED.can_manage_categories,
            can_review_documents = EXCLUDED.can_review_documents,
            can_review_plans = EXCLUDED.can_review_plans,
            can_review_ai_chat = EXCLUDED.can_review_ai_chat,
            can_review_logs = EXCLUDED.can_review_logs,
            can_manage_permissions = EXCLUDED.can_manage_permissions,
            updated_at = now();
    END IF;
END $$;

ALTER TABLE users DROP CONSTRAINT IF EXISTS users_role_fkey;
ALTER TABLE users
    ADD CONSTRAINT users_role_fkey
    FOREIGN KEY (role) REFERENCES role_permissions(role);

DROP TABLE IF EXISTS staff_permissions;

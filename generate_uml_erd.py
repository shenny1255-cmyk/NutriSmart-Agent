import os
from PIL import Image, ImageDraw, ImageFont

# Canvas setup - Minimalist & Compact without Header Title
WIDTH = 3200
HEIGHT = 2800
bg_color = (255, 255, 255)
border_color = (70, 80, 95)
header_bg = (240, 243, 246)
header_text = (15, 23, 42)
text_color = (30, 41, 59)
type_color = (100, 116, 139)
line_color = (71, 85, 105)
card_color = (180, 40, 40)

image = Image.new("RGB", (WIDTH, HEIGHT), color=bg_color)
draw = ImageDraw.Draw(image)

# Load fonts
try:
    font_bold = ImageFont.truetype("arialbd.ttf", 18)
    font_regular = ImageFont.truetype("arial.ttf", 15)
    font_small = ImageFont.truetype("arial.ttf", 13)
    font_card = ImageFont.truetype("arialbd.ttf", 14)
except Exception:
    font_bold = ImageFont.load_default()
    font_regular = ImageFont.load_default()
    font_small = ImageFont.load_default()
    font_card = ImageFont.load_default()

tables = [
    # --- COLUMN 1 (x = 80): USERS & HEALTH PROFILES ---
    {
        "name": "users", "pos": (80, 40),
        "cols": [
            ("id", "UUID", "[PK]"),
            ("email", "VARCHAR(255)", "UNIQUE"),
            ("password_hash", "VARCHAR(255)", ""),
            ("role", "user_role", "ENUM"),
            ("created_at", "TIMESTAMPTZ", ""),
            ("updated_at", "TIMESTAMPTZ", ""),
        ]
    },
    {
        "name": "user_profile", "pos": (80, 270),
        "cols": [
            ("user_id", "UUID", "[PK, FK → users]"),
            ("full_name", "VARCHAR(150)", ""),
            ("gender", "gender_enum", "ENUM"),
            ("birth_date", "DATE", ""),
            ("activity_level_id", "SMALLINT", "[FK → activity_levels]"),
            ("goal", "goal_enum", "ENUM"),
            ("daily_calorie_target", "INTEGER", ""),
            ("custom_conditions", "JSONB", ""),
            ("custom_allergens", "JSONB", ""),
            ("created_at", "TIMESTAMPTZ", ""),
            ("updated_at", "TIMESTAMPTZ", ""),
        ]
    },
    {
        "name": "activity_levels", "pos": (80, 2100),
        "cols": [
            ("id", "SMALLINT", "[PK]"),
            ("name", "VARCHAR(100)", "UNIQUE"),
            ("description", "VARCHAR(500)", ""),
            ("calorie_multiplier", "NUMERIC(4,3)", ""),
        ]
    },
    {
        "name": "staff_profiles", "pos": (80, 710),
        "cols": [
            ("user_id", "UUID", "[PK, FK → users]"),
            ("staff_code", "VARCHAR(30)", "UNIQUE"),
            ("full_name", "VARCHAR(150)", ""),
            ("gender", "VARCHAR(10)", ""),
            ("birth_date", "DATE", ""),
            ("specialization", "VARCHAR(100)", ""),
            ("qualification", "VARCHAR(100)", ""),
            ("employment_status", "VARCHAR(20)", ""),
            ("created_at", "TIMESTAMPTZ", ""),
            ("updated_at", "TIMESTAMPTZ", ""),
        ]
    },
    {
        "name": "role_permissions", "pos": (80, 1050),
        "cols": [
            ("role", "user_role", "[PK]"),
            ("can_manage_users", "BOOLEAN", ""),
            ("can_manage_foods", "BOOLEAN", ""),
            ("can_manage_categories", "BOOLEAN", ""),
            ("can_review_documents", "BOOLEAN", ""),
            ("can_review_plans", "BOOLEAN", ""),
            ("can_review_ai_chat", "BOOLEAN", ""),
            ("can_review_logs", "BOOLEAN", ""),
            ("can_manage_permissions", "BOOLEAN", ""),
            ("created_at", "TIMESTAMPTZ", ""),
            ("updated_at", "TIMESTAMPTZ", ""),
        ]
    },
    {
        "name": "medical_conditions", "pos": (80, 1420),
        "cols": [
            ("id", "INTEGER", "[PK]"),
            ("name", "VARCHAR(150)", "UNIQUE"),
        ]
    },
    {
        "name": "allergens", "pos": (80, 1590),
        "cols": [
            ("id", "INTEGER", "[PK]"),
            ("name", "VARCHAR(150)", "UNIQUE"),
        ]
    },
    {
        "name": "user_medical_conditions", "pos": (80, 1730),
        "cols": [
            ("user_id", "UUID", "[PK, FK → user_profile]"),
            ("condition_id", "INTEGER", "[PK, FK → med_cond]"),
        ]
    },
    {
        "name": "user_allergens", "pos": (80, 1870),
        "cols": [
            ("user_id", "UUID", "[PK, FK → user_profile]"),
            ("allergen_id", "INTEGER", "[PK, FK → allergens]"),
        ]
    },

    # --- COLUMN 2 (x = 720): TRACKING & LOGS ---
    {
        "name": "foods", "pos": (720, 40),
        "cols": [
            ("id", "UUID", "[PK]"),
            ("name", "VARCHAR(200)", ""),
            ("serving_desc", "VARCHAR(100)", ""),
            ("serving_gram", "NUMERIC(7,2)", ""),
            ("calories_kcal", "NUMERIC(7,2)", ""),
            ("protein_g", "NUMERIC(6,2)", ""),
            ("carb_g", "NUMERIC(6,2)", ""),
            ("fat_g", "NUMERIC(6,2)", ""),
            ("source", "VARCHAR(100)", ""),
        ]
    },
    {
        "name": "exercises", "pos": (720, 350),
        "cols": [
            ("id", "INTEGER", "[PK]"),
            ("name", "VARCHAR(150)", ""),
            ("met_value", "NUMERIC(4,2)", ""),
            ("category", "VARCHAR(80)", ""),
        ]
    },
    {
        "name": "meal_images", "pos": (720, 550),
        "cols": [
            ("id", "UUID", "[PK]"),
            ("user_id", "UUID", "[FK → users]"),
            ("image_path", "TEXT", ""),
            ("status", "job_status", "ENUM"),
            ("predicted_food_id", "UUID", "[FK → foods]"),
            ("confidence", "NUMERIC(4,3)", ""),
            ("raw_prediction", "JSONB", ""),
            ("estimated_kcal", "NUMERIC(7,2)", ""),
            ("suitability_note", "TEXT", ""),
            ("created_at", "TIMESTAMPTZ", ""),
        ]
    },
    {
        "name": "meal_logs", "pos": (720, 900),
        "cols": [
            ("id", "BIGINT", "[PK]"),
            ("user_id", "UUID", "[FK → users]"),
            ("food_id", "UUID", "[FK → foods]"),
            ("meal_image_id", "UUID", "[FK → meal_images]"),
            ("meal_type", "meal_type", "ENUM"),
            ("quantity", "NUMERIC(6,2)", ""),
            ("calories_kcal", "NUMERIC(7,2)", ""),
            ("logged_at", "TIMESTAMPTZ", ""),
            ("log_date", "DATE", ""),
        ]
    },
    {
        "name": "activity_logs", "pos": (720, 1240),
        "cols": [
            ("id", "BIGINT", "[PK]"),
            ("user_id", "UUID", "[FK → users]"),
            ("exercise_id", "INTEGER", "[FK → exercises]"),
            ("steps", "INTEGER", ""),
            ("duration_min", "INTEGER", ""),
            ("calories_burned", "NUMERIC(7,2)", ""),
            ("started_at", "TIMESTAMPTZ", ""),
            ("ended_at", "TIMESTAMPTZ", ""),
            ("logged_at", "TIMESTAMPTZ", ""),
        ]
    },
    {
        "name": "body_metrics_history", "pos": (720, 1580),
        "cols": [
            ("id", "BIGINT", "[PK]"),
            ("user_id", "UUID", "[FK → users]"),
            ("recorded_at", "DATE", ""),
            ("height_cm", "NUMERIC(5,2)", ""),
            ("weight_kg", "NUMERIC(5,2)", ""),
        ]
    },

    # --- COLUMN 3 (x = 1360): PLANS & CHECKINS ---
    {
        "name": "nutrition_plans", "pos": (1360, 40),
        "cols": [
            ("id", "UUID", "[PK]"),
            ("user_id", "UUID", "[FK → users]"),
            ("parent_plan_id", "UUID", "[FK → plans]"),
            ("version", "INTEGER", ""),
            ("start_date", "DATE", ""),
            ("end_date", "DATE", ""),
            ("daily_kcal_target", "INTEGER", ""),
            ("goal", "goal_enum", "ENUM"),
            ("content", "JSONB", ""),
            ("status", "plan_status", "ENUM"),
            ("created_at", "TIMESTAMPTZ", ""),
        ]
    },
    {
        "name": "plan_evaluations", "pos": (1360, 450),
        "cols": [
            ("id", "BIGINT", "[PK]"),
            ("plan_id", "UUID", "[FK → plans]"),
            ("period_start", "DATE", ""),
            ("period_end", "DATE", ""),
            ("avg_kcal_intake", "NUMERIC(8,2)", ""),
            ("weight_change_kg", "NUMERIC(5,2)", ""),
            ("result", "eval_result", "ENUM"),
            ("ai_feedback", "TEXT", ""),
            ("evaluated_at", "TIMESTAMPTZ", ""),
        ]
    },
    {
        "name": "plan_checkin_series", "pos": (1360, 770),
        "cols": [
            ("id", "UUID", "[PK]"),
            ("user_id", "UUID", "[FK → users]"),
            ("goal", "goal_enum", "ENUM"),
            ("status", "VARCHAR(20)", ""),
            ("started_at", "DATE", ""),
            ("closed_at", "DATE", ""),
            ("created_at", "TIMESTAMPTZ", ""),
        ]
    },
    {
        "name": "plan_checkins", "pos": (1360, 1060),
        "cols": [
            ("id", "UUID", "[PK]"),
            ("series_id", "UUID", "[FK → series]"),
            ("user_id", "UUID", "[FK → users]"),
            ("plan_id", "UUID", "[FK → plans]"),
            ("adjusted_plan_id", "UUID", "[FK → plans]"),
            ("previous_checkin_id", "UUID", "[FK → checkins]"),
            ("period_number", "INTEGER", ""),
            ("start_date", "DATE", ""),
            ("period_end", "DATE", ""),
            ("baseline_weight_kg", "NUMERIC(5,2)", ""),
            ("actual_weight_kg", "NUMERIC(5,2)", ""),
            ("adherence_pct", "SMALLINT", ""),
            ("status", "VARCHAR(20)", ""),
            ("created_at", "TIMESTAMPTZ", ""),
        ]
    },

    # --- COLUMN 4 (x = 2000): RAG, CHAT & AUDIT ---
    {
        "name": "crawl_sources", "pos": (2000, 40),
        "cols": [
            ("id", "UUID", "[PK]"),
            ("name", "VARCHAR(255)", ""),
            ("source_key", "VARCHAR(100)", "UNIQUE"),
            ("domain", "VARCHAR(255)", ""),
            ("base_urls", "JSONB", ""),
            ("is_active", "BOOLEAN", ""),
            ("created_at", "TIMESTAMPTZ", ""),
            ("updated_at", "TIMESTAMPTZ", ""),
        ]
    },
    {
        "name": "doc_categories", "pos": (2000, 310),
        "cols": [
            ("id", "INTEGER", "[PK]"),
            ("parent_id", "INTEGER", "[FK → doc_cat]"),
            ("name", "VARCHAR(150)", ""),
            ("slug", "VARCHAR(150)", "UNIQUE"),
        ]
    },
    {
        "name": "documents", "pos": (2000, 520),
        "cols": [
            ("id", "UUID", "[PK]"),
            ("category_id", "INTEGER", "[FK → doc_cat]"),
            ("title", "TEXT", ""),
            ("source_url", "TEXT", ""),
            ("source_name", "VARCHAR(150)", ""),
            ("language", "VARCHAR(10)", ""),
            ("file_path", "TEXT", ""),
            ("raw_text", "TEXT", ""),
            ("status", "doc_status", "ENUM"),
            ("uploaded_by", "UUID", "[FK → users]"),
            ("approved_by", "UUID", "[FK → users]"),
            ("approved_at", "TIMESTAMPTZ", ""),
            ("created_at", "TIMESTAMPTZ", ""),
            ("deleted_at", "TIMESTAMPTZ", ""),
        ]
    },
    {
        "name": "doc_chunks", "pos": (2000, 1000),
        "cols": [
            ("id", "BIGINT", "[PK]"),
            ("document_id", "UUID", "[FK → documents]"),
            ("chunk_index", "INTEGER", ""),
            ("content", "TEXT", ""),
            ("token_count", "INTEGER", ""),
            ("embedding", "VECTOR(1024)", ""),
            ("metadata", "JSONB", ""),
        ]
    },
    {
        "name": "chat_sessions", "pos": (2000, 1290),
        "cols": [
            ("id", "UUID", "[PK]"),
            ("user_id", "UUID", "[FK → users]"),
            ("title", "VARCHAR(255)", ""),
            ("created_at", "TIMESTAMPTZ", ""),
        ]
    },
    {
        "name": "chat_messages", "pos": (2000, 1500),
        "cols": [
            ("id", "INTEGER", "[PK]"),
            ("session_id", "UUID", "[FK → sessions]"),
            ("role", "VARCHAR(20)", ""),
            ("content", "TEXT", ""),
            ("flagged", "BOOLEAN", ""),
            ("created_at", "TIMESTAMPTZ", ""),
        ]
    },
    {
        "name": "message_citations", "pos": (2000, 1740),
        "cols": [
            ("message_id", "BIGINT", "[PK, FK → msg]"),
            ("chunk_id", "BIGINT", "[PK, FK → chunk]"),
            ("score", "NUMERIC(5,4)", ""),
            ("rank", "SMALLINT", ""),
        ]
    },
    {
        "name": "notifications", "pos": (2000, 1950),
        "cols": [
            ("id", "BIGINT", "[PK]"),
            ("user_id", "UUID", "[FK → users]"),
            ("type", "VARCHAR(50)", ""),
            ("title", "VARCHAR(200)", ""),
            ("body", "TEXT", ""),
            ("is_read", "BOOLEAN", ""),
            ("created_at", "TIMESTAMPTZ", ""),
        ]
    },
    {
        "name": "audit_logs", "pos": (2000, 2210),
        "cols": [
            ("id", "BIGINT", "[PK]"),
            ("actor_id", "UUID", "[FK → users]"),
            ("action", "VARCHAR(50)", ""),
            ("entity", "VARCHAR(80)", ""),
            ("entity_id", "TEXT", ""),
            ("before_data", "JSONB", ""),
            ("after_data", "JSONB", ""),
            ("ip_address", "INET", ""),
            ("created_at", "TIMESTAMPTZ", ""),
        ]
    }
]

# Chừa khoảng trống phía trên và giữa các cột để đi đường quan hệ mà không cắt qua bảng.
column_x = {80: 80, 720: 900, 1360: 1720, 2000: 2540}
top_offset = 200
for table in tables:
    old_x, old_y = table["pos"]
    table["pos"] = (column_x[old_x], old_y + top_offset)

# Render Table Boxes
table_boxes = {}

for tbl in tables:
    x, y = tbl["pos"]
    cols = tbl["cols"]

    box_w = 580
    row_h = 24
    header_h = 32
    box_h = header_h + len(cols) * row_h + 8

    table_boxes[tbl["name"]] = (x, y, box_w, box_h)

    # Outer Border
    draw.rectangle([x, y, x + box_w, y + box_h], fill=(255, 255, 255), outline=border_color, width=1)

    # Header
    draw.rectangle([x, y, x + box_w, y + header_h], fill=header_bg, outline=border_color, width=1)
    draw.text((x + box_w // 2, y + header_h // 2), tbl["name"], fill=header_text, font=font_bold, anchor="mm")

    # Column rows
    cy = y + header_h + 4
    for c_name, c_type, c_tag in cols:
        draw.text((x + 12, cy + 2), c_name, fill=text_color, font=font_regular)
        tag_str = f"  {c_tag}" if c_tag else ""
        draw.text((x + box_w - 12, cy + 2), f"{c_type}{tag_str}", fill=type_color, font=font_small, anchor="ra")
        cy += row_h

# CONNECTIONS (Clean Connector Lines)
connections = [
    # Người dùng và hồ sơ
    ("role_permissions", "users", "1", "0..*", ""),
    ("users", "user_profile", "1", "0..1", ""),
    ("activity_levels", "user_profile", "0..1", "0..*", ""),
    ("users", "staff_profiles", "1", "0..1", ""),
    ("user_profile", "user_medical_conditions", "1", "0..*", ""),
    ("medical_conditions", "user_medical_conditions", "1", "0..*", ""),
    ("user_profile", "user_allergens", "1", "0..*", ""),
    ("allergens", "user_allergens", "1", "0..*", ""),

    # Theo dõi dinh dưỡng và vận động
    ("users", "meal_images", "1", "0..*", ""),
    ("foods", "meal_images", "0..1", "0..*", ""),
    ("users", "meal_logs", "1", "0..*", ""),
    ("foods", "meal_logs", "0..1", "0..*", ""),
    ("meal_images", "meal_logs", "0..1", "0..*", ""),
    ("users", "activity_logs", "1", "0..*", ""),
    ("exercises", "activity_logs", "0..1", "0..*", ""),
    ("users", "body_metrics_history", "1", "0..*", ""),

    # Lộ trình và check-in
    ("users", "nutrition_plans", "0..1", "0..*", ""),
    ("nutrition_plans", "nutrition_plans", "0..1", "0..*", "parent_plan_id"),
    ("nutrition_plans", "plan_evaluations", "1", "0..*", ""),
    ("users", "plan_checkin_series", "1", "0..*", ""),
    ("plan_checkin_series", "plan_checkins", "1", "0..*", ""),
    ("users", "plan_checkins", "1", "0..*", ""),
    ("nutrition_plans", "plan_checkins", "0..1", "0..*", "plan_id / adjusted_plan_id"),
    ("plan_checkins", "plan_checkins", "0..1", "0..*", "previous_checkin_id"),

    # Tài liệu RAG
    ("doc_categories", "doc_categories", "0..1", "0..*", "parent_id"),
    ("doc_categories", "documents", "0..1", "0..*", ""),
    ("users", "documents", "0..1", "0..*", "uploaded_by / approved_by"),
    ("documents", "doc_chunks", "1", "0..*", ""),

    # Chat, thông báo và kiểm toán
    ("users", "chat_sessions", "1", "0..*", ""),
    ("chat_sessions", "chat_messages", "0..1", "0..*", ""),
    ("chat_messages", "message_citations", "1", "0..*", ""),
    ("doc_chunks", "message_citations", "1", "0..*", ""),
    ("users", "notifications", "1", "0..*", ""),
    ("users", "audit_logs", "0..1", "0..*", ""),
]

column_indexes = {
    table["name"]: {column[0]: index for index, column in enumerate(table["cols"])}
    for table in tables
}


def draw_label(position, label):
    """Vẽ nhãn khóa ngoại với nền trắng để không bị chìm vào đường nối."""
    if not label:
        return
    bbox = draw.textbbox(position, label, font=font_small, anchor="mm")
    draw.rectangle(
        [bbox[0] - 3, bbox[1] - 2, bbox[2] + 3, bbox[3] + 2],
        fill=bg_color,
    )
    draw.text(position, label, fill=type_color, font=font_small, anchor="mm")


# Cột dùng làm cổng nối cho từng quan hệ. Nhờ bám đúng hàng FK, người đọc có thể
# nhận ra ngay cột nào tạo quan hệ thay vì phải suy ra từ một đường nối ở tiêu đề.
connection_ports = {
    ("role_permissions", "users", ""): ("role", "role"),
    ("users", "user_profile", ""): ("id", "user_id"),
    ("activity_levels", "user_profile", ""): ("id", "activity_level_id"),
    ("users", "staff_profiles", ""): ("id", "user_id"),
    ("user_profile", "user_medical_conditions", ""): ("user_id", "user_id"),
    ("medical_conditions", "user_medical_conditions", ""): ("id", "condition_id"),
    ("user_profile", "user_allergens", ""): ("user_id", "user_id"),
    ("allergens", "user_allergens", ""): ("id", "allergen_id"),
    ("users", "meal_images", ""): ("id", "user_id"),
    ("foods", "meal_images", ""): ("id", "predicted_food_id"),
    ("users", "meal_logs", ""): ("id", "user_id"),
    ("foods", "meal_logs", ""): ("id", "food_id"),
    ("meal_images", "meal_logs", ""): ("id", "meal_image_id"),
    ("users", "activity_logs", ""): ("id", "user_id"),
    ("exercises", "activity_logs", ""): ("id", "exercise_id"),
    ("users", "body_metrics_history", ""): ("id", "user_id"),
    ("users", "nutrition_plans", ""): ("id", "user_id"),
    ("nutrition_plans", "nutrition_plans", "parent_plan_id"): ("id", "parent_plan_id"),
    ("nutrition_plans", "plan_evaluations", ""): ("id", "plan_id"),
    ("users", "plan_checkin_series", ""): ("id", "user_id"),
    ("plan_checkin_series", "plan_checkins", ""): ("id", "series_id"),
    ("users", "plan_checkins", ""): ("id", "user_id"),
    ("nutrition_plans", "plan_checkins", "plan_id / adjusted_plan_id"): (
        "id",
        ("plan_id", "adjusted_plan_id"),
    ),
    ("plan_checkins", "plan_checkins", "previous_checkin_id"): ("id", "previous_checkin_id"),
    ("doc_categories", "doc_categories", "parent_id"): ("id", "parent_id"),
    ("doc_categories", "documents", ""): ("id", "category_id"),
    ("users", "documents", "uploaded_by / approved_by"): (
        "id",
        ("uploaded_by", "approved_by"),
    ),
    ("documents", "doc_chunks", ""): ("id", "document_id"),
    ("users", "chat_sessions", ""): ("id", "user_id"),
    ("chat_sessions", "chat_messages", ""): ("id", "session_id"),
    ("chat_messages", "message_citations", ""): ("id", "message_id"),
    ("doc_chunks", "message_citations", ""): ("id", "chunk_id"),
    ("users", "notifications", ""): ("id", "user_id"),
    ("users", "audit_logs", ""): ("id", "actor_id"),
}


def row_center(table_name, columns):
    """Trả về tâm một hàng cột, hoặc tâm của nhiều hàng khi một cặp bảng có nhiều FK."""
    if isinstance(columns, str):
        columns = (columns,)
    _, table_y, _, _ = table_boxes[table_name]
    centers = [
        table_y + header_h + 4 + column_indexes[table_name][column] * row_h + row_h // 2
        for column in columns
    ]
    return sum(centers) // len(centers)


def draw_cardinality(position, value, anchor="mm"):
    """Vẽ cardinality trên nền trắng để không bị đường nối đi xuyên qua chữ."""
    bbox = draw.textbbox(position, value, font=font_card, anchor=anchor)
    draw.rectangle(
        [bbox[0] - 2, bbox[1] - 1, bbox[2] + 2, bbox[3] + 1],
        fill=bg_color,
    )
    draw.text(position, value, fill=card_color, font=font_card, anchor=anchor)


def right_gutter_center(table_x, table_width):
    """Tâm vùng trống bên phải bảng, dùng để đặt nhãn quan hệ dài."""
    next_columns = sorted(x for x in column_x.values() if x > table_x)
    right_boundary = next_columns[0] if next_columns else WIDTH
    return (table_x + table_width + right_boundary) // 2


# Những FK từ users tới cột khác cùng đi qua vùng trống phía trên. Mỗi đích có
# một làn dọc riêng trong khe giữa hai cột, nên không có đường chéo cắt qua bảng.
user_cross_relations = [
    relation
    for relation in connections
    if relation[0] == "users"
    and table_boxes[relation[0]][0] != table_boxes[relation[1]][0]
]
user_cross_indexes = {
    (src, dst, label): index
    for index, (src, dst, _src_card, _dst_card, label) in enumerate(user_cross_relations)
}
target_lane_indexes = {}
same_column_lane_indexes = {}

for src, dst, src_card, dst_card, label in connections:
    sx, sy, sw, sh = table_boxes[src]
    dx, dy, dw, dh = table_boxes[dst]
    source_column, target_column = connection_ports[(src, dst, label)]
    source_y = row_center(src, source_column)
    target_y = row_center(dst, target_column)

    if src == dst:
        # Quan hệ tự tham chiếu có vòng nhỏ riêng sát cạnh phải của bảng.
        loop_x = sx + sw + 20
        draw.line(
            [(sx + sw, source_y), (loop_x, source_y), (loop_x, target_y), (sx + sw, target_y)],
            fill=line_color,
            width=2,
        )
        draw_cardinality((sx + sw + 5, source_y - 9), src_card, anchor="lm")
        draw_cardinality((sx + sw + 5, target_y + 9), dst_card, anchor="lm")
        draw_label((right_gutter_center(sx, sw), (source_y + target_y) // 2), label)
        continue

    if src == "users" and sx != dx:
        relation_index = user_cross_indexes[(src, dst, label)]
        top_lane_y = 24 + relation_index * 18
        target_lane_index = target_lane_indexes.get(dx, 0)
        target_lane_indexes[dx] = target_lane_index + 1
        target_lane_x = dx - 18 - target_lane_index * 16
        users_bus_x = sx + sw + 30

        draw.line(
            [
                (sx + sw, source_y),
                (users_bus_x, source_y),
                (users_bus_x, top_lane_y),
                (target_lane_x, top_lane_y),
                (target_lane_x, target_y),
                (dx, target_y),
            ],
            fill=line_color,
            width=2,
        )
        draw_cardinality((users_bus_x + 6, top_lane_y), src_card, anchor="lm")
        draw_cardinality((dx - 5, target_y - 9), dst_card, anchor="rm")
        draw_label(((users_bus_x + target_lane_x) // 2, top_lane_y), label)
        continue

    if sx == dx:
        # Quan hệ trong cùng cột đi vòng ngoài mép bảng bằng các làn song song.
        lane_key = sx
        lane_index = same_column_lane_indexes.get(lane_key, 0)
        same_column_lane_indexes[lane_key] = lane_index + 1
        use_left_side = sx == min(column_x.values())

        if use_left_side:
            lane_x = sx - 16 - lane_index * 8
            source_x = target_x = sx
            source_anchor = target_anchor = "rm"
            cardinality_x = sx - 5
        else:
            lane_x = sx + sw + 40 + lane_index * 12
            source_x = target_x = sx + sw
            source_anchor = target_anchor = "lm"
            cardinality_x = sx + sw + 5

        draw.line(
            [(source_x, source_y), (lane_x, source_y), (lane_x, target_y), (target_x, target_y)],
            fill=line_color,
            width=2,
        )
        draw_cardinality((cardinality_x, source_y - 9), src_card, anchor=source_anchor)
        draw_cardinality((cardinality_x, target_y + 9), dst_card, anchor=target_anchor)
        draw_label((right_gutter_center(sx, sw), (source_y + target_y) // 2), label)
        continue

    # Nhánh dự phòng cho quan hệ khác cột không xuất phát từ users.
    middle_x = (sx + sw + dx) // 2
    draw.line(
        [(sx + sw, source_y), (middle_x, source_y), (middle_x, target_y), (dx, target_y)],
        fill=line_color,
        width=2,
    )
    draw_cardinality((sx + sw + 5, source_y - 9), src_card, anchor="lm")
    draw_cardinality((dx - 5, target_y - 9), dst_card, anchor="rm")
    draw_label((middle_x, (source_y + target_y) // 2), label)

output_path = "backend/er_diagram.png"
image.save(output_path, "PNG")
print(f"Saved clean ERD image without header title to {output_path}")

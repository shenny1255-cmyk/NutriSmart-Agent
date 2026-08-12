import os
from PIL import Image, ImageDraw, ImageFont

# Canvas setup - Minimalist & Compact without Header Title
WIDTH = 2700
HEIGHT = 2850
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
        "name": "user_info", "pos": (80, 270),
        "cols": [
            ("user_id", "UUID", "[PK, FK → users]"),
            ("full_name", "VARCHAR(150)", ""),
            ("gender", "gender_enum", "ENUM"),
            ("birth_date", "DATE", ""),
            ("height_cm", "NUMERIC(5,2)", ""),
            ("weight_kg", "NUMERIC(5,2)", ""),
            ("activity_level", "SMALLINT", ""),
            ("goal", "goal_enum", "ENUM"),
            ("daily_calorie_target", "INTEGER", ""),
            ("custom_conditions", "JSONB", ""),
            ("custom_allergens", "JSONB", ""),
            ("created_at", "TIMESTAMPTZ", ""),
            ("updated_at", "TIMESTAMPTZ", ""),
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
        "name": "staff_permissions", "pos": (80, 1050),
        "cols": [
            ("user_id", "UUID", "[PK, FK → staff]"),
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
        "name": "profile_conditions", "pos": (80, 1730),
        "cols": [
            ("user_id", "UUID", "[PK, FK → user_info]"),
            ("condition_id", "INTEGER", "[PK, FK → med_cond]"),
        ]
    },
    {
        "name": "profile_allergens", "pos": (80, 1870),
        "cols": [
            ("user_id", "UUID", "[PK, FK → user_info]"),
            ("allergen_id", "INTEGER", "[PK, FK → allergens]"),
            ("severity", "SMALLINT", ""),
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
    # Column 1
    ("users", "user_info", "1", "0..1"),
    ("users", "staff_profiles", "1", "0..1"),
    ("staff_profiles", "staff_permissions", "1", "1..1"),
    ("user_info", "profile_conditions", "1", "0..*"),
    ("medical_conditions", "profile_conditions", "1", "0..*"),
    ("user_info", "profile_allergens", "1", "0..*"),
    ("allergens", "profile_allergens", "1", "0..*"),

    # Column 2
    ("foods", "meal_images", "0..1", "0..*"),
    ("foods", "meal_logs", "0..1", "0..*"),
    ("meal_images", "meal_logs", "0..1", "0..*"),
    ("exercises", "activity_logs", "0..1", "0..*"),
    ("activity_logs", "body_metrics_history", "1", "0..*"),

    # Column 3
    ("nutrition_plans", "plan_evaluations", "1", "0..*"),
    ("plan_checkin_series", "plan_checkins", "1", "0..*"),
    ("nutrition_plans", "plan_checkins", "1", "0..*"),

    # Column 4
    ("crawl_sources", "documents", "0..1", "0..*"),
    ("doc_categories", "documents", "0..1", "0..*"),
    ("documents", "doc_chunks", "1", "0..*"),
    ("chat_sessions", "chat_messages", "1", "0..*"),
    ("chat_messages", "message_citations", "1", "0..*"),
    ("doc_chunks", "message_citations", "1", "0..*"),
    ("chat_messages", "notifications", "1", "0..*"),
    ("notifications", "audit_logs", "1", "0..*"),

    # Cross-Column connections
    ("user_info", "body_metrics_history", "1", "0..*"),
    ("meal_logs", "nutrition_plans", "0..*", "1"),
    ("plan_checkins", "chat_sessions", "0..1", "0..*"),
]

for src, dst, src_card, dst_card in connections:
    if src in table_boxes and dst in table_boxes:
        sx, sy, sw, sh = table_boxes[src]
        dx, dy, dw, dh = table_boxes[dst]

        if sx + sw < dx:  # src left of dst
            start_pt = (sx + sw, sy + 30)
            end_pt = (dx, dy + 30)
            start_txt_pos = (sx + sw + 6, sy + 15)
            end_txt_pos = (dx - 28, dy + 15)
        elif dx + dw < sx:  # dst left of src
            start_pt = (sx, sy + 30)
            end_pt = (dx + dw, dy + 30)
            start_txt_pos = (sx - 25, sy + 15)
            end_txt_pos = (dx + dw + 6, dy + 15)
        else:  # Vertical Stack
            if sy < dy:
                start_pt = (sx + sw // 2, sy + sh)
                end_pt = (dx + dw // 2, dy)
                start_txt_pos = (sx + sw // 2 + 6, sy + sh + 4)
                end_txt_pos = (dx + dw // 2 + 6, dy - 18)
            else:
                start_pt = (sx + sw // 2, sy)
                end_pt = (dx + dw // 2, dy + dh)
                start_txt_pos = (sx + sw // 2 + 6, sy - 18)
                end_txt_pos = (dx + dw // 2 + 6, dy + dh + 4)

        draw.line([start_pt, end_pt], fill=line_color, width=2)
        draw.text(start_txt_pos, src_card, fill=card_color, font=font_card)
        draw.text(end_txt_pos, dst_card, fill=card_color, font=font_card)

output_path = "backend/er_diagram.png"
image.save(output_path, "PNG")
print(f"Saved clean ERD image without header title to {output_path}")

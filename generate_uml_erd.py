import os, math
from PIL import Image, ImageDraw, ImageFont

# Canvas setup
WIDTH = 2500
HEIGHT = 4200
bg_color = (255, 255, 255)
border_color = (40, 40, 40)
header_bg = (235, 240, 245)
text_color = (20, 20, 20)
type_color = (80, 80, 80)
line_color = (50, 60, 100)      # Dark visible blue-gray lines
card_color = (180, 40, 40)      # Dark red for cardinality labels (1, 0..*)

image = Image.new("RGB", (WIDTH, HEIGHT), color=bg_color)
draw = ImageDraw.Draw(image)

# Load fonts
try:
    font_bold = ImageFont.truetype("arialbd.ttf", 20)
    font_regular = ImageFont.truetype("arial.ttf", 16)
    font_small = ImageFont.truetype("arial.ttf", 14)
    font_card = ImageFont.truetype("arialbd.ttf", 15)
    font_title = ImageFont.truetype("arialbd.ttf", 28)
except Exception:
    font_bold = ImageFont.load_default()
    font_regular = ImageFont.load_default()
    font_small = ImageFont.load_default()
    font_card = ImageFont.load_default()
    font_title = ImageFont.load_default()

# Title Header
draw.text((WIDTH // 2, 45), "NUTRISMART AGENT - DATABASE ER DIAGRAM (24 TABLES)", fill=(10, 30, 60), font=font_title, anchor="mm")
draw.text((WIDTH // 2, 85), "Đồng bộ 100% theo implementation_plan.md (Table-per-Role Pattern - 24 Bảng Chuẩn)", fill=(90, 90, 90), font=font_regular, anchor="mm")

tables = [
    # --- COLUMN 1 (Left: x=100) ---
    {
        "name": "foods",
        "pos": (100, 150),
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
        "name": "exercises",
        "pos": (100, 500),
        "cols": [
            ("id", "INTEGER", "[PK]"),
            ("name", "VARCHAR(150)", ""),
            ("met_value", "NUMERIC(4,2)", ""),
            ("category", "VARCHAR(80)", ""),
        ]
    },
    {
        "name": "meal_images",
        "pos": (100, 720),
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
        "name": "meal_logs",
        "pos": (100, 1100),
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
        "name": "activity_logs",
        "pos": (100, 1460),
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
        "name": "doc_categories",
        "pos": (100, 1820),
        "cols": [
            ("id", "INTEGER", "[PK]"),
            ("parent_id", "INTEGER", "[FK → doc_categories]"),
            ("name", "VARCHAR(150)", ""),
            ("slug", "VARCHAR(150)", "UNIQUE"),
        ]
    },
    {
        "name": "documents",
        "pos": (100, 2070),
        "cols": [
            ("id", "UUID", "[PK]"),
            ("category_id", "INTEGER", "[FK → doc_categories]"),
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
        "name": "doc_chunks",
        "pos": (100, 2570),
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

    # --- COLUMN 2 (Center: x=900) ---
    {
        "name": "users",
        "pos": (900, 150),
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
        "name": "user_info",
        "pos": (900, 440),
        "cols": [
            ("user_id", "UUID", "[PK, FK → users]"),
            ("full_name", "VARCHAR(150)", ""),
            ("gender", "VARCHAR(10)", ""),
            ("birth_date", "DATE", ""),
            ("height_cm", "NUMERIC(5,2)", ""),
            ("weight_kg", "NUMERIC(5,2)", ""),
            ("bmi", "NUMERIC(5,2)", "GENERATED"),
            ("activity_level", "SMALLINT", ""),
            ("goal", "VARCHAR(20)", ""),
            ("daily_calorie_target", "INTEGER", ""),
            ("created_at", "TIMESTAMPTZ", ""),
            ("updated_at", "TIMESTAMPTZ", ""),
        ]
    },
    {
        "name": "staff_profiles",
        "pos": (900, 860),
        "cols": [
            ("user_id", "UUID", "[PK, FK → users]"),
            ("staff_code", "VARCHAR(30)", "UNIQUE"),
            ("full_name", "VARCHAR(150)", ""),
            ("gender", "VARCHAR(10)", ""),
            ("birth_date", "DATE", ""),
            ("specialization", "VARCHAR(100)", ""),
            ("qualification", "VARCHAR(100)", ""),
            ("employment_status", "VARCHAR(20)", "DEFAULT 'ACTIVE'"),
            ("created_at", "TIMESTAMPTZ", ""),
            ("updated_at", "TIMESTAMPTZ", ""),
        ]
    },
    {
        "name": "staff_permissions",
        "pos": (900, 1230),
        "cols": [
            ("user_id", "UUID", "[PK, FK → staff_profiles]"),
            ("can_manage_users", "BOOLEAN", "DEFAULT false"),
            ("can_manage_foods", "BOOLEAN", "DEFAULT false"),
            ("can_manage_categories", "BOOLEAN", "DEFAULT false"),
            ("can_review_documents", "BOOLEAN", "DEFAULT false"),
            ("can_review_plans", "BOOLEAN", "DEFAULT false"),
            ("can_review_ai_chat", "BOOLEAN", "DEFAULT false"),
            ("can_review_logs", "BOOLEAN", "DEFAULT false"),
            ("can_manage_permissions", "BOOLEAN", "DEFAULT false"),
            ("created_at", "TIMESTAMPTZ", ""),
            ("updated_at", "TIMESTAMPTZ", ""),
        ]
    },
    {
        "name": "body_metrics_history",
        "pos": (900, 1630),
        "cols": [
            ("id", "BIGINT", "[PK]"),
            ("user_id", "UUID", "[FK → users]"),
            ("recorded_at", "DATE", ""),
            ("weight_kg", "NUMERIC(5,2)", ""),
            ("bmi", "NUMERIC(5,2)", ""),
        ]
    },
    {
        "name": "audit_logs",
        "pos": (900, 1890),
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
    },
    {
        "name": "notifications",
        "pos": (900, 2250),
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

    # --- COLUMN 3 (Right: x=1700) ---
    {
        "name": "medical_conditions",
        "pos": (1700, 150),
        "cols": [
            ("id", "INTEGER", "[PK]"),
            ("code", "VARCHAR(50)", "UNIQUE"),
            ("name", "VARCHAR(150)", ""),
        ]
    },
    {
        "name": "allergens",
        "pos": (1700, 360),
        "cols": [
            ("id", "INTEGER", "[PK]"),
            ("name", "VARCHAR(150)", "UNIQUE"),
        ]
    },
    {
        "name": "profile_conditions",
        "pos": (1700, 520),
        "cols": [
            ("user_id", "UUID", "[PK, FK → user_info]"),
            ("condition_id", "INTEGER", "[PK, FK → medical_conditions]"),
        ]
    },
    {
        "name": "profile_allergens",
        "pos": (1700, 700),
        "cols": [
            ("user_id", "UUID", "[PK, FK → user_info]"),
            ("allergen_id", "INTEGER", "[PK, FK → allergens]"),
            ("severity", "SMALLINT", ""),
        ]
    },
    {
        "name": "nutrition_plans",
        "pos": (1700, 920),
        "cols": [
            ("id", "UUID", "[PK]"),
            ("user_id", "UUID", "[FK → users]"),
            ("version", "INTEGER", ""),
            ("start_date", "DATE", ""),
            ("end_date", "DATE", ""),
            ("daily_kcal_target", "INTEGER", ""),
            ("goal", "goal_enum", "ENUM"),
            ("content", "JSONB", ""),
            ("generated_by", "VARCHAR(100)", ""),
            ("status", "plan_status", "ENUM"),
            ("created_at", "TIMESTAMPTZ", ""),
        ]
    },
    {
        "name": "plan_evaluations",
        "pos": (1700, 1340),
        "cols": [
            ("id", "BIGINT", "[PK]"),
            ("plan_id", "UUID", "[FK → nutrition_plans]"),
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
        "name": "chat_sessions",
        "pos": (1700, 1680),
        "cols": [
            ("id", "UUID", "[PK]"),
            ("user_id", "UUID", "[FK → users]"),
            ("title", "VARCHAR(255)", ""),
            ("created_at", "TIMESTAMPTZ", ""),
        ]
    },
    {
        "name": "chat_messages",
        "pos": (1700, 1920),
        "cols": [
            ("id", "INTEGER", "[PK]"),
            ("session_id", "UUID", "[FK → chat_sessions]"),
            ("role", "VARCHAR(20)", ""),
            ("content", "TEXT", ""),
            ("flagged", "BOOLEAN", ""),
            ("created_at", "TIMESTAMPTZ", ""),
        ]
    },
    {
        "name": "message_citations",
        "pos": (1700, 2180),
        "cols": [
            ("message_id", "BIGINT", "[PK, FK → chat_messages]"),
            ("chunk_id", "BIGINT", "[PK, FK → doc_chunks]"),
            ("score", "NUMERIC(5,4)", ""),
            ("rank", "SMALLINT", ""),
        ]
    }
]

# Helper to render table box
table_boxes = {}

for tbl in tables:
    x, y = tbl["pos"]
    cols = tbl["cols"]

    box_w = 480
    row_h = 24
    header_h = 32
    box_h = header_h + len(cols) * row_h + 8

    table_boxes[tbl["name"]] = (x, y, box_w, box_h)

    # Draw Outer Border
    draw.rectangle([x, y, x + box_w, y + box_h], fill=(255, 255, 255), outline=border_color, width=1)

    # Header Fill
    draw.rectangle([x, y, x + box_w, y + header_h], fill=header_bg, outline=border_color, width=1)

    draw.text((x + box_w // 2, y + header_h // 2), tbl["name"], fill=(0, 0, 0), font=font_bold, anchor="mm")

    # Column rows
    cy = y + header_h + 4
    for c_name, c_type, c_tag in cols:
        tag_str = f" {c_tag}" if c_tag else ""
        col_text = f" {c_name}"
        type_text = f"{c_type}{tag_str} "

        draw.text((x + 10, cy + 2), col_text, fill=text_color, font=font_regular)
        draw.text((x + box_w - 10, cy + 2), type_text, fill=type_color, font=font_small, anchor="ra")

        cy += row_h

# Relationships with explicit cardinalities (src, dst, src_card, dst_card)
connections = [
    ("users", "user_info", "1", "0..1"),
    ("users", "staff_profiles", "1", "0..1"),
    ("staff_profiles", "staff_permissions", "1", "1..1"),
    ("users", "body_metrics_history", "1", "0..*"),
    ("users", "audit_logs", "1", "0..*"),
    ("users", "notifications", "1", "0..*"),
    ("users", "nutrition_plans", "1", "0..*"),
    ("users", "chat_sessions", "1", "0..*"),
    ("users", "meal_images", "1", "0..*"),
    ("users", "activity_logs", "1", "0..*"),
    ("users", "meal_logs", "1", "0..*"),

    ("user_info", "profile_conditions", "1", "0..*"),
    ("medical_conditions", "profile_conditions", "1", "0..*"),
    ("user_info", "profile_allergens", "1", "0..*"),
    ("allergens", "profile_allergens", "1", "0..*"),

    ("nutrition_plans", "plan_evaluations", "1", "0..*"),
    ("foods", "meal_logs", "0..1", "0..*"),
    ("meal_images", "meal_logs", "0..1", "0..*"),
    ("exercises", "activity_logs", "0..1", "0..*"),
    ("foods", "meal_images", "0..1", "0..*"),

    ("chat_sessions", "chat_messages", "1", "0..*"),
    ("chat_messages", "message_citations", "1", "0..*"),
    ("doc_chunks", "message_citations", "1", "0..*"),

    ("doc_categories", "documents", "0..1", "0..*"),
    ("documents", "doc_chunks", "1", "0..*"),
]

for src, dst, src_card, dst_card in connections:
    if src in table_boxes and dst in table_boxes:
        sx, sy, sw, sh = table_boxes[src]
        dx, dy, dw, dh = table_boxes[dst]

        # Determine edge anchor points
        if sx + sw < dx:  # src is left of dst
            start_pt = (sx + sw, sy + 30)
            end_pt = (dx, dy + 30)
            start_txt_pos = (sx + sw + 8, sy + 15)
            end_txt_pos = (dx - 25, dy + 15)
        elif dx + dw < sx:  # dst is left of src
            start_pt = (sx, sy + 30)
            end_pt = (dx + dw, dy + 30)
            start_txt_pos = (sx - 20, sy + 15)
            end_txt_pos = (dx + dw + 8, dy + 15)
        else:  # vertically stacked
            if sy < dy:
                start_pt = (sx + sw // 2, sy + sh)
                end_pt = (dx + dw // 2, dy)
                start_txt_pos = (sx + sw // 2 + 6, sy + sh + 5)
                end_txt_pos = (dx + dw // 2 + 6, dy - 20)
            else:
                start_pt = (sx + sw // 2, sy)
                end_pt = (dx + dw // 2, dy + dh)
                start_txt_pos = (sx + sw // 2 + 6, sy - 20)
                end_txt_pos = (dx + dw // 2 + 6, dy + dh + 5)

        # Draw clear line
        draw.line([start_pt, end_pt], fill=line_color, width=2)

        # Draw cardinality labels
        draw.text(start_txt_pos, src_card, fill=card_color, font=font_card)
        draw.text(end_txt_pos, dst_card, fill=card_color, font=font_card)

output_path = "backend/er_diagram.png"
image.save(output_path, "PNG")
print(f"Saved clean 24-table UML ERD image to {output_path}")

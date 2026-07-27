from datetime import date, timedelta
import random

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.deps import get_db
from app.models import (
    User, HealthProfile, NutritionPlan, ProfileCondition, ProfileAllergen
)
from app.security import hash_password, create_access_token
from app.services.calorie import daily_calorie_target

router = APIRouter(prefix="/demo", tags=["demo"])

DEMO_EMAIL = "demo@nutrismart.vn"
DEMO_PASSWORD = "demo1234"

# Tài khoản phụ để Admin quản lý
EXTRA_DEMO_USERS = [
    {"email": "user1@nutrismart.vn",   "full_name": "Nguyễn Văn An",    "role": "USER"},
    {"email": "user2@nutrismart.vn",   "full_name": "Trần Thị Bích",    "role": "USER"},
    {"email": "expert1@nutrismart.vn", "full_name": "BS. Lê Minh Quang", "role": "EXPERT"},
]


@router.post("/seed")
def seed_demo(db: Session = Depends(get_db)):
    """Tạo (hoặc reset) tài khoản demo kèm dữ liệu mẫu. Trả về access_token."""

    # 1. Xóa tài khoản demo cũ nếu có (CASCADE dọn sạch profile, logs, plan...)
    all_demo_emails = [DEMO_EMAIL] + [u["email"] for u in EXTRA_DEMO_USERS]
    old_users = db.query(User).filter(User.email.in_(all_demo_emails)).all()
    for old in old_users:
        # Các bảng FK → users.id không có ON DELETE CASCADE → xóa thủ công
        uid = str(old.id)
        db.execute(text("DELETE FROM audit_logs WHERE actor_id = :uid"), {"uid": uid})
        db.execute(text("DELETE FROM documents WHERE uploaded_by = :uid OR approved_by = :uid"), {"uid": uid})
        db.execute(text("DELETE FROM drug_country_rules WHERE updated_by = :uid"), {"uid": uid})
        db.delete(old)
    db.flush()

    # 2. Tạo user demo
    user = User(
        email=DEMO_EMAIL,
        password_hash=hash_password(DEMO_PASSWORD),
        full_name="Người dùng Demo",
        country_code="VN",
        role="ADMIN",
        email_verified=True,
    )
    db.add(user)
    db.flush()

    # 2b. Tạo thêm user demo phụ (USER + EXPERT) để Admin quản lý
    for u in EXTRA_DEMO_USERS:
        db.add(User(
            email=u["email"],
            password_hash=hash_password(DEMO_PASSWORD),
            full_name=u["full_name"],
            country_code="VN",
            role=u["role"],
            email_verified=True,
        ))
    db.flush()

    # 3. Hồ sơ sức khỏe
    profile_args = dict(
        gender="MALE",
        birth_date=date(2000, 1, 1),
        height_cm=170,
        weight_kg=68,
        activity_level=3,
        goal="LOSE_WEIGHT",
    )
    target = daily_calorie_target(**profile_args)

    profile = HealthProfile(
        user_id=user.id,
        daily_calorie_target=target,
        **profile_args,
    )
    db.add(profile)
    db.flush()

    # 4. Gắn 1 bệnh nền + 1 dị ứng (nếu seed catalog có id 1)
    if db.execute(text("SELECT 1 FROM medical_conditions WHERE id = 1")).first():
        db.add(ProfileCondition(profile_id=profile.id, condition_id=1))
    if db.execute(text("SELECT 1 FROM allergens WHERE id = 1")).first():
        db.add(ProfileAllergen(profile_id=profile.id, allergen_id=1, severity=2))

    # 5. Lấy sẵn id món ăn + bài tập từ seed
    food_ids = [r[0] for r in db.execute(text("SELECT id FROM foods LIMIT 5")).all()]
    ex_ids = [r[0] for r in db.execute(text("SELECT id FROM exercises LIMIT 3")).all()]

    # 6. Nhật ký ăn uống + vận động cho 7 ngày gần nhất
    for d in range(6, -1, -1):
        day = date.today() - timedelta(days=d)

        # 3 bữa/ngày
        if food_ids:
            for meal, ratio in [("BREAKFAST", 0.3), ("LUNCH", 0.4), ("DINNER", 0.3)]:
                fid = random.choice(food_ids)
                kcal = round(target * ratio + random.randint(-80, 120), 1)
                db.execute(text("""
                    INSERT INTO meal_logs
                        (user_id, food_id, meal_type, quantity, calories_kcal, logged_at, log_date)
                    VALUES (:uid, :fid, :mt, 1, :kcal, :ts, :d)
                """), {
                    "uid": str(user.id), "fid": str(fid), "mt": meal,
                    "kcal": kcal, "ts": f"{day} 12:00:00", "d": day,
                })

        # 1 buổi vận động/ngày
        if ex_ids:
            db.execute(text("""
                INSERT INTO activity_logs
                    (user_id, exercise_id, steps, duration_min, calories_burned, log_date)
                VALUES (:uid, :eid, :steps, :dur, :burn, :d)
            """), {
                "uid": str(user.id), "eid": random.choice(ex_ids),
                "steps": random.randint(4000, 9000),
                "dur": random.randint(20, 50),
                "burn": random.randint(180, 400),
                "d": day,
            })

    # 6b. Mốc cân nặng 7 ngày (giảm dần) để job đánh giá tính được weight_change_kg
    for d in range(6, -1, -1):
        db.execute(text("""
            INSERT INTO body_metrics_history (user_id, recorded_at, weight_kg)
            VALUES (:uid, :d, :w)
            ON CONFLICT (user_id, recorded_at) DO UPDATE SET weight_kg = EXCLUDED.weight_kg
        """), {
            "uid": str(user.id),
            "d": date.today() - timedelta(days=d),
            "w": round(float(profile_args["weight_kg"]) + d * 0.1, 2),
        })

    # 7. Một lộ trình đang active
    plan_content = {
        "days": [
            {
                "meals": [
                    {"type": "Sáng", "name": "Phở bò", "kcal": int(target * 0.3)},
                    {"type": "Trưa", "name": "Cơm gà + rau luộc", "kcal": int(target * 0.4)},
                    {"type": "Tối", "name": "Salad ức gà", "kcal": int(target * 0.3)},
                ],
                "exercise": "Đi bộ 30 phút",
            }
            for _ in range(7)
        ]
    }
    plan = NutritionPlan(
        user_id=user.id,
        version=1,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=7),
        daily_kcal_target=target,
        goal="LOSE_WEIGHT",
        content=plan_content,
        generated_by="demo-seed",
        status="ACTIVE",
    )
    db.add(plan)

    # Vài tài liệu chờ duyệt để demo màn Expert (kèm raw_text để test luồng Chunking & Embedding)
    sample_docs = [
        (
            "Hướng dẫn dinh dưỡng cho người tiểu đường típ 2",
            "https://moh.gov.vn",
            "Người mắc bệnh đái tháo đường típ 2 cần kiểm soát nghiêm ngặt chỉ số đường huyết. Ưu tiên thực phẩm có chỉ số đường huyết GI thấp như rau xanh, ngũ cốc nguyên hạt, đậu đỗ. Hạn chế tối đa đường tinh chế, nước ngọt có ga, bánh kẹo. Chia nhỏ khẩu phần thành 3 bữa chính và 1-2 bữa phụ để tránh tăng đường huyết đột ngột sau ăn."
        ),
        (
            "Khuyến nghị lượng đạm theo cân nặng - WHO",
            "https://who.int",
            "Theo khuyến nghị của Tổ chức Y tế Thế giới (WHO), lượng đạm tối thiểu cho người trưởng thành là 0.8g/kg trọng lượng cơ thể mỗi ngày. Với người tham gia tập luyện thể thao hoặc vận động nặng, nhu cầu đạm tăng lên 1.2g - 2.0g/kg/ngày. Nguồn đạm chất lượng cao bao gồm thịt ức gà, cá biển, trứng, sữa tươi và các loại đậu."
        ),
        (
            "Thành phần dinh dưỡng thực phẩm Việt Nam",
            "https://fdc.nal.usda.gov",
            "Việc nắm rõ hàm lượng calo và dinh dưỡng đa lượng trong các món ăn Việt Nam giúp kiểm soát cân nặng tốt hơn. Một tô phở bò trung bình cung cấp 430 kcal cùng 25g protein. Một dĩa cơm tấm sườn nướng cung cấp 620 kcal. Việc kết hợp rau xanh và tập luyện giúp đốt cháy năng lượng dư thừa."
        ),
    ]

    for title, src, raw_content in sample_docs:
        db.execute(text("""
            INSERT INTO documents (id, title, source_url, source_name, raw_text, status, uploaded_by)
            VALUES (gen_random_uuid(), :t, :u, :s, :raw, 'PENDING', :uid)
        """), {"t": title, "u": src, "s": src, "raw": raw_content, "uid": str(user.id)})

    # Seed mẫu Thuốc và Quy định thuốc theo quốc gia (nếu chưa có)
    db.execute(text("ALTER TABLE drugs ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;"))
    db.execute(text("""
        INSERT INTO drug_categories (id, name) VALUES (1, 'Thuốc giảm cân'), (2, 'Thuốc cảm sốt')
        ON CONFLICT DO NOTHING;
    """))
    sample_drugs = [
        ('a0000000-0000-0000-0000-000000000001', 1, 'Sibutramine', 'Sibutramine', 'Hỗ trợ giảm cân', 'Tăng huyết áp, nguy cơ đột quỵ, tim mạch', 'Bệnh tim mạch, tăng huyết áp chưa kiểm soát'),
        ('a0000000-0000-0000-0000-000000000002', 1, 'Reductil', 'Sibutramine', 'Giảm cân', 'Tăng nguy cơ biến cố tim mạch', 'Tiền sử bệnh mạch vành, đột quỵ'),
        ('a0000000-0000-0000-0000-000000000003', 1, 'Phentermine', 'Phentermine', 'Giảm thèm ăn', 'Tăng nhịp tim, mất ngủ, nghiện', 'Bệnh tim, tăng áp phổi'),
        ('a0000000-0000-0000-0000-000000000004', 2, 'Pseudoephedrine', 'Pseudoephedrine', 'Giảm sung huyết mũi', 'Tăng huyết áp, hồi hộp', 'Bệnh tăng huyết áp nặng'),
        ('a0000000-0000-0000-0000-000000000005', 2, 'Paracetamol', 'Paracetamol', 'Giảm đau hạ sốt', 'Hại gan khi dùng quá liều', 'Suy gan nặng'),
    ]
    for did, cid, name, active, ind, side, contra in sample_drugs:
        db.execute(text("""
            INSERT INTO drugs (id, category_id, name, active_ingredient, indications, side_effects, contraindications)
            VALUES (:id, :cid, :n, :a, :i, :s, :c)
            ON CONFLICT DO NOTHING;
        """), {"id": did, "cid": cid, "n": name, "a": active, "i": ind, "s": side, "c": contra})

    sample_rules = [
        ('a0000000-0000-0000-0000-000000000001', 'VN', 'BANNED', 'Bị cấm lưu hành tại Việt Nam do nguy cơ tim mạch và đột quỵ nghiêm trọng.'),
        ('a0000000-0000-0000-0000-000000000002', 'VN', 'BANNED', 'Bị rút giấy phép lưu hành tại Việt Nam do chứa Sibutramine.'),
        ('a0000000-0000-0000-0000-000000000003', 'VN', 'BANNED', 'Cấm sử dụng trong thực phẩm chức năng và thuốc giảm cân không kê đơn tại Việt Nam.'),
        ('a0000000-0000-0000-0000-000000000004', 'VN', 'RESTRICTED', 'Thuốc kê đơn, cần quản lý đặc biệt và có chỉ định của bác sĩ tại Việt Nam.'),
        ('a0000000-0000-0000-0000-000000000005', 'VN', 'ALLOWED', 'Được phép sử dụng theo đúng liều lượng khuyến cáo.'),
    ]
    for did, cc, st, note in sample_rules:
        db.execute(text("""
            INSERT INTO drug_country_rules (drug_id, country_code, status, note, updated_by)
            VALUES (:did, :cc, :st, :note, :uid)
            ON CONFLICT (drug_id, country_code) DO UPDATE SET status = EXCLUDED.status, note = EXCLUDED.note;
        """), {"did": did, "cc": cc, "st": st, "note": note, "uid": str(user.id)})

    db.commit()

    return {
        "access_token": create_access_token(str(user.id)),
        "email": DEMO_EMAIL,
        "message": "Đã tạo tài khoản demo kèm dữ liệu mẫu 7 ngày.",
    }
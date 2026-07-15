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

    # Vài tài liệu chờ duyệt để demo màn Expert
    for i, (title, src) in enumerate([
        ("Hướng dẫn dinh dưỡng cho người tiểu đường típ 2", "https://moh.gov.vn"),
        ("Khuyến nghị lượng đạm theo cân nặng - WHO", "https://who.int"),
        ("Thành phần dinh dưỡng thực phẩm Việt Nam", "https://fdc.nal.usda.gov"),
    ]):
        db.execute(text("""
            INSERT INTO documents (id, title, source_url, source_name, status, uploaded_by)
            VALUES (gen_random_uuid(), :t, :u, :s, 'PENDING', :uid)
        """), {"t": title, "u": src, "s": src, "uid": str(user.id)})

    db.commit()

    return {
        "access_token": create_access_token(str(user.id)),
        "email": DEMO_EMAIL,
        "message": "Đã tạo tài khoản demo kèm dữ liệu mẫu 7 ngày.",
    }
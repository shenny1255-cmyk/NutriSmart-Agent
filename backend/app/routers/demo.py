from datetime import date, timedelta
import random
from typing import TypedDict

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.deps import get_db
from app.models import (
    User, UserProfile, NutritionPlan, UserMedicalCondition, UserAllergen
)
from app.security import hash_password, create_access_token
from app.services.calorie import daily_calorie_target
from app.services import plan_checkin
from app.services.activity_levels import get_activity_level

router = APIRouter(prefix="/demo", tags=["demo"])

DEMO_EMAIL = "demo@nutrismart.vn"
DEMO_PASSWORD = "demo1234"
DEMO_NAME = "Người dùng Demo"


class DemoProfileArgs(TypedDict):
    gender: str
    birth_date: date
    height_cm: float
    weight_kg: float
    activity_level: int
    goal: str

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
    old_users = db.query(User).filter(User.email.in_(all_demo_emails)).all()  # type: ignore
    for old in old_users:
        # Các bảng FK → users.id không có ON DELETE CASCADE → xóa thủ công
        uid = str(old.id)
        db.execute(text("DELETE FROM audit_logs WHERE actor_id = :uid"), {"uid": uid})
        db.execute(text("DELETE FROM documents WHERE uploaded_by = :uid OR approved_by = :uid"), {"uid": uid})
        db.delete(old)
    db.flush()

    # 2. Tạo user demo
    user = User(
        email=DEMO_EMAIL,
        password_hash=hash_password(DEMO_PASSWORD),
        full_name="Người dùng Demo",
        role="ADMIN",
    )
    db.add(user)
    db.flush()

    # 2b. Tạo thêm user demo phụ (USER + EXPERT) để Admin quản lý
    from app.models import StaffProfile
    import uuid
    # Hồ sơ nhân viên của Admin; quyền được lấy chung theo role.
    sp_admin = StaffProfile(
        user_id=user.id,
        staff_code=f"STF-ADM{uuid.uuid4().hex[:4].upper()}",
        full_name=user.full_name or "Tài khoản Demo Admin",
        employment_status="ACTIVE",
    )
    db.add(sp_admin)

    for idx, u in enumerate(EXTRA_DEMO_USERS, start=1):
        extra_u = User(
            email=u["email"],
            password_hash=hash_password(DEMO_PASSWORD),
            role=u["role"],
        )
        extra_u.profile = UserProfile(user_id=extra_u.id, full_name=u["full_name"])
        db.add(extra_u)
        db.flush()
        if u["role"] in ("EXPERT", "ADMIN"):
            sp_extra = StaffProfile(
                user_id=extra_u.id,
                staff_code=f"STF-EXP{idx:03d}",
                full_name=u["full_name"],
                specialization="Dinh dưỡng lâm sàng",
                qualification="Thạc sĩ Y học",
                employment_status="ACTIVE",
            )
            db.add(sp_extra)
    db.flush()

    # 3. Hồ sơ sức khỏe (nằm trong user_profile)
    profile_args: DemoProfileArgs = {
        "gender": "MALE",
        "birth_date": date(2000, 1, 1),
        "height_cm": 170.0,
        "weight_kg": 68.0,
        "activity_level": 3,
        "goal": "LOSE_WEIGHT",
    }
    target = daily_calorie_target(  # type: ignore
        gender=str(profile_args["gender"]),
        birth_date=profile_args["birth_date"],  # type: ignore
        height_cm=float(profile_args["height_cm"]),  # type: ignore
        weight_kg=float(profile_args["weight_kg"]),  # type: ignore
        activity_multiplier=float(
            get_activity_level(db, int(profile_args["activity_level"])).calorie_multiplier
        ),
        goal=str(profile_args["goal"]),
    )

    if not user.profile:
        user.profile = UserProfile(user_id=user.id, full_name=DEMO_NAME)
    for k, v in profile_args.items():
        if k in {"height_cm", "weight_kg"}:
            continue
        setattr(user.profile, k, v)
    user.profile.daily_calorie_target = target
    db.flush()

    # 4. Gắn 1 bệnh nền + 1 dị ứng (nếu seed catalog có id 1)
    if db.execute(text("SELECT 1 FROM medical_conditions WHERE id = 1")).first():
        db.add(UserMedicalCondition(user_id=user.id, condition_id=1))
    if db.execute(text("SELECT 1 FROM allergens WHERE id = 1")).first():
        db.add(UserAllergen(user_id=user.id, allergen_id=1))

    # 5. Lấy sẵn món ăn (kèm calo thật) + bài tập từ seed
    mon_an = db.execute(text(
        "SELECT id, calories_kcal FROM foods WHERE calories_kcal > 0 ORDER BY name LIMIT 12"
    )).all()
    ex_ids = [r[0] for r in db.execute(text("SELECT id FROM exercises LIMIT 3")).all()]

    # 6. Nhật ký ăn uống + vận động cho 7 ngày gần nhất
    for d in range(6, -1, -1):
        day = date.today() - timedelta(days=d)

        # 3 bữa/ngày — số phần suy ra từ calo THẬT của món để dòng nhật ký khớp
        if mon_an:
            for meal, ratio in [("BREAKFAST", 0.3), ("LUNCH", 0.4), ("DINNER", 0.3)]:
                fid, kcal_mon = random.choice(mon_an)
                phan = max(0.5, round((target * ratio) / float(kcal_mon) * 2) / 2)
                kcal = round(float(kcal_mon) * phan, 1)
                db.execute(text("""
                    INSERT INTO meal_logs
                        (user_id, food_id, meal_type, quantity, calories_kcal, logged_at, log_date)
                    VALUES (:uid, :fid, :mt, :qty, :kcal, :ts, :d)
                """), {
                    "uid": str(user.id), "fid": str(fid), "mt": meal, "qty": phan,
                    "kcal": kcal, "ts": f"{day} 12:00:00", "d": day,
                })

        # 1 buổi vận động/ngày
        if ex_ids:
            dur = random.randint(20, 50)
            db.execute(text("""
                INSERT INTO activity_logs
                    (user_id, exercise_id, steps, duration_min, calories_burned, started_at, ended_at, logged_at)
                VALUES (:uid, :eid, :steps, :dur, :burn, :s_at, :e_at, :l_at)
            """), {
                "uid": str(user.id), "eid": random.choice(ex_ids),
                "steps": random.randint(4000, 9000),
                "dur": dur,
                "burn": random.randint(180, 400),
                "s_at": f"{day} 07:00:00",
                "e_at": f"{day} 07:{dur:02d}:00",
                "l_at": f"{day} 08:00:00",
            })

    # 6b. Mốc cân nặng 7 ngày (giảm dần) để job đánh giá tính được weight_change_kg
    for d in range(6, -1, -1):
        db.execute(text("""
            INSERT INTO body_metrics_history (user_id, recorded_at, height_cm, weight_kg)
            VALUES (:uid, :d, :h, :w)
            ON CONFLICT (user_id, recorded_at) DO UPDATE
            SET height_cm = EXCLUDED.height_cm, weight_kg = EXCLUDED.weight_kg
        """), {
            "uid": str(user.id),
            "d": date.today() - timedelta(days=d),
            "h": profile_args["height_cm"],
            "w": round(float(profile_args["weight_kg"]) + d * 0.1, 2),  # type: ignore
        })

    # 7. Một lộ trình đang active và đã đến hạn check-in 14 ngày
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
        start_date=date.today() - timedelta(days=14),
        end_date=date.today() - timedelta(days=1),
        daily_kcal_target=target,
        goal="LOSE_WEIGHT",
        content=plan_content,
        status="ACTIVE",
    )
    db.add(plan)
    db.flush()
    plan_checkin.start_new_series(db, user, plan, today=date.today() - timedelta(days=14))

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

    db.commit()

    return {
        "access_token": create_access_token(str(user.id)),
        "email": DEMO_EMAIL,
        "message": "Đã tạo tài khoản demo kèm dữ liệu và kỳ check-in 14 ngày đến hạn.",
    }

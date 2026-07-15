from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.deps import get_db, get_current_user
from app.models import User, HealthProfile, ProfileCondition, ProfileAllergen
from app.schemas import RegisterIn, LoginIn, TokenOut, UserOut
from app.security import hash_password, verify_password, create_access_token
from app.services.calorie import daily_calorie_target

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenOut, status_code=201)
def register(payload: RegisterIn, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():  # type: ignore
        raise HTTPException(status.HTTP_409_CONFLICT, "Email đã được sử dụng")

    p = payload.profile

    try:
        # 1. users
        user = User(
            email=payload.email,
            password_hash=hash_password(payload.password),
            full_name=payload.full_name,
            country_code=payload.country_code,
            role="USER",
        )
        db.add(user)
        db.flush()   # lấy user.id mà CHƯA commit

        # 2. health_profiles + tính mục tiêu calo
        target = daily_calorie_target(
            gender=p.gender,
            birth_date=p.birth_date,
            height_cm=p.height_cm,
            weight_kg=p.weight_kg,
            activity_level=p.activity_level,
            goal=p.goal,
        )

        profile = HealthProfile(
            user_id=user.id,
            gender=p.gender,
            birth_date=p.birth_date,
            height_cm=p.height_cm,
            weight_kg=p.weight_kg,
            activity_level=p.activity_level,
            goal=p.goal,
            daily_calorie_target=target,
            # KHÔNG set bmi — generated column
        )
        db.add(profile)
        db.flush()

        # 3. bệnh nền + dị ứng (nhiều-nhiều)
        for cid in p.condition_ids:
            db.add(ProfileCondition(profile_id=profile.id, condition_id=cid))
        for aid in p.allergen_ids:
            db.add(ProfileAllergen(profile_id=profile.id, allergen_id=aid))

        db.commit()

    except Exception:
        db.rollback()   # thất bại giữa chừng → không để lại user mồ côi
        raise

    return TokenOut(access_token=create_access_token(str(user.id)))


@router.post("/login", response_model=TokenOut)
def login(payload: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email, User.deleted_at.is_(None)).first()  # type: ignore

    # Thông báo chung cho cả 2 trường hợp — tránh lộ email nào đã đăng ký
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Email hoặc mật khẩu không đúng")

    return TokenOut(access_token=create_access_token(str(user.id)))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user
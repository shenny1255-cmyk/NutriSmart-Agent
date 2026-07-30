from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.deps import get_db, get_current_user
from app.models import User, HealthProfile, ProfileCondition, ProfileAllergen
from app.schemas import RegisterIn, LoginIn, TokenOut, UserOut, MeOut, UserProfileUpdateIn
from app.security import (
    hash_password, verify_password, create_access_token,
    create_verification_token, decode_verification_token,
)
from app.services.calorie import daily_calorie_target
from app.services.email import build_verify_link, send_verification_email

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

    # Gửi email xác minh (lỗi gửi mail đã được nuốt bên trong, không làm hỏng đăng ký)
    verify_token = create_verification_token(str(user.id))
    send_verification_email(user.email, build_verify_link(verify_token))

    return TokenOut(access_token=create_access_token(str(user.id)))


@router.get("/verify")
def verify_email(token: str, db: Session = Depends(get_db)):
    user_id = decode_verification_token(token)
    if not user_id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Liên kết xác minh không hợp lệ hoặc đã hết hạn",
        )
    user = db.query(User).filter(User.id == user_id).first()  # type: ignore
    if not user:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Người dùng không tồn tại")

    if not user.email_verified:
        user.email_verified = True
        db.commit()
    return {"status": "verified"}


@router.post("/resend-verification")
def resend_verification(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.email_verified:
        return {"status": "already_verified"}
    verify_token = create_verification_token(str(user.id))
    send_verification_email(user.email, build_verify_link(verify_token))
    return {"status": "sent"}


@router.post("/login", response_model=TokenOut)
def login(payload: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email, User.deleted_at.is_(None)).first()  # type: ignore

    # Thông báo chung cho cả 2 trường hợp — tránh lộ email nào đã đăng ký
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Email hoặc mật khẩu không đúng")

    return TokenOut(access_token=create_access_token(str(user.id)))


@router.get("/me", response_model=MeOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.put("/me", response_model=MeOut)
def update_me(
    payload: UserProfileUpdateIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Cập nhật thông tin cá nhân + hồ sơ sức khỏe của chính mình."""
    # 1. Cập nhật user
    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.country_code is not None:
        user.country_code = payload.country_code

    # 2. Cập nhật hồ sơ sức khỏe (tạo mới nếu chưa có)
    profile = user.profile
    if profile is None:
        profile = HealthProfile(user_id=user.id)
        db.add(profile)
        db.flush()

    profile_fields = ["gender", "birth_date", "height_cm", "weight_kg",
                      "activity_level", "goal"]
    changed_profile = False
    for field in profile_fields:
        val = getattr(payload, field)
        if val is not None:
            setattr(profile, field, val)
            changed_profile = True

    # 3. Tính lại calo mục tiêu nếu hồ sơ đầy đủ và có thay đổi
    if changed_profile and all([
        profile.gender, profile.birth_date, profile.height_cm,
        profile.weight_kg, profile.activity_level, profile.goal,
    ]):
        profile.daily_calorie_target = daily_calorie_target(
            gender=profile.gender,
            birth_date=profile.birth_date,
            height_cm=float(profile.height_cm),
            weight_kg=float(profile.weight_kg),
            activity_level=profile.activity_level,
            goal=profile.goal,
        )

    # 4. Cập nhật bệnh nền + dị ứng nếu có gửi lên
    if payload.condition_ids is not None:
        db.query(ProfileCondition).filter(
            ProfileCondition.profile_id == profile.id
        ).delete()
        for cid in payload.condition_ids:
            db.add(ProfileCondition(profile_id=profile.id, condition_id=cid))

    if payload.allergen_ids is not None:
        db.query(ProfileAllergen).filter(
            ProfileAllergen.profile_id == profile.id
        ).delete()
        for aid in payload.allergen_ids:
            db.add(ProfileAllergen(profile_id=profile.id, allergen_id=aid))

    db.commit()
    db.refresh(user)
    db.refresh(profile)
    return user
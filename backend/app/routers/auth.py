from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.deps import get_db, get_current_user
from app.models import User, UserInfo, ProfileCondition, ProfileAllergen
from app.schemas import (
    RegisterIn, LoginIn, TokenOut, UserOut, MeOut, ProfileOut, UserProfileUpdateIn,
    EmailAvailabilityIn, EmailAvailabilityOut,
    validate_body_metrics,
)
from app.security import (
    hash_password, verify_password, create_access_token,
    create_verification_token, decode_verification_token,
)
from app.services.calorie import daily_calorie_target
from app.services.email import build_verify_link, send_verification_email

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/check-email", response_model=EmailAvailabilityOut)
def check_email_availability(payload: EmailAvailabilityIn, db: Session = Depends(get_db)):
    exists = db.query(User).filter(User.email == payload.email).first()  # type: ignore
    return EmailAvailabilityOut(available=exists is None)


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
            role="USER",
        )
        db.add(user)
        db.flush()   # lấy user.id mà CHƯA commit

        # 2. user_info + tính mục tiêu calo
        target = daily_calorie_target(
            gender=p.gender,
            birth_date=p.birth_date,
            height_cm=p.height_cm,
            weight_kg=p.weight_kg,
            activity_level=p.activity_level,
            goal=p.goal,
        )

        info = UserInfo(
            user_id=user.id,
            full_name=payload.full_name,
            gender=p.gender,
            birth_date=p.birth_date,
            height_cm=p.height_cm,
            weight_kg=p.weight_kg,
            activity_level=p.activity_level,
            goal=p.goal,
            daily_calorie_target=target,
            custom_conditions=p.custom_conditions,
            custom_allergens=[item.model_dump() for item in p.custom_allergens],
            # KHÔNG set bmi — generated column
        )
        db.add(info)
        db.flush()

        # 3. bệnh nền + dị ứng (nhiều-nhiều)
        for cid in p.condition_ids:
            db.add(ProfileCondition(user_id=user.id, condition_id=cid))
        for aid in p.allergen_ids:
            db.add(ProfileAllergen(user_id=user.id, allergen_id=aid))

        db.commit()

    except Exception:
        db.rollback()   # thất bại giữa chừng → không để lại user mồ côi
        raise

    # Gửi email xác minh (lỗi gửi mail đã được nuốt bên trong, không làm hỏng đăng ký)
    verify_token = create_verification_token(str(user.id))
    send_verification_email(str(user.email), build_verify_link(verify_token))

    return TokenOut(access_token=create_access_token(str(user.id)))


@router.get("/verify")
def verify_email(token: str, db: Session = Depends(get_db)):
    user_id = decode_verification_token(token)
    if not user_id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Mã xác thực không hợp lệ",
        )
    import uuid
    user = db.query(User).filter(User.id == uuid.UUID(user_id)).first()  # type: ignore
    if not user:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Người dùng không tồn tại")

    return {"status": "verified"}


@router.post("/resend-verification")
def resend_verification():
    return {"status": "already_verified"}


@router.post("/login", response_model=TokenOut)
def login(payload: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()  # type: ignore

    # Thông báo chung cho cả 2 trường hợp — tránh lộ email nào đã đăng ký
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Email hoặc mật khẩu không đúng")

    return TokenOut(access_token=create_access_token(str(user.id)))


@router.get("/me", response_model=MeOut)
def me(user: User = Depends(get_current_user)):
    profile_out = ProfileOut.model_validate(user.info) if user.info else None
    return MeOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        staff_profile=user.staff_profile,
        profile=profile_out,
    )


@router.put("/me", response_model=MeOut)
def update_me(
    payload: UserProfileUpdateIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Cập nhật thông tin cá nhân + hồ sơ sức khỏe của chính mình."""
    info = user.info
    if info is None:
        info = UserInfo(user_id=user.id)
        db.add(info)
        db.flush()

    if payload.full_name is not None:
        info.full_name = payload.full_name

    if payload.height_cm is not None or payload.weight_kg is not None:
        next_height = payload.height_cm if payload.height_cm is not None else info.height_cm
        next_weight = payload.weight_kg if payload.weight_kg is not None else info.weight_kg
        if next_height is not None and next_weight is not None:
            validate_body_metrics(float(next_height), float(next_weight))

    profile_fields = ["gender", "birth_date", "height_cm", "weight_kg",
                      "activity_level", "goal"]
    changed_profile = False
    for field in profile_fields:
        val = getattr(payload, field)
        if val is not None:
            setattr(info, field, val)
            changed_profile = True

    # Tính lại calo mục tiêu nếu hồ sơ đầy đủ và có thay đổi
    if changed_profile and all([
        info.gender, info.birth_date, info.height_cm,
        info.weight_kg, info.activity_level, info.goal,
    ]):
        info.daily_calorie_target = daily_calorie_target(  # type: ignore
            gender=str(info.gender),
            birth_date=info.birth_date,  # type: ignore
            height_cm=float(info.height_cm),  # type: ignore
            weight_kg=float(info.weight_kg),  # type: ignore
            activity_level=int(info.activity_level),  # type: ignore
            goal=str(info.goal),
        )

    # Cập nhật bệnh nền + dị ứng nếu có gửi lên
    if payload.condition_ids is not None:
        db.query(ProfileCondition).filter(
            ProfileCondition.user_id == user.id
        ).delete()
        for cid in payload.condition_ids:
            db.add(ProfileCondition(user_id=user.id, condition_id=cid))

    if payload.allergen_ids is not None:
        db.query(ProfileAllergen).filter(
            ProfileAllergen.user_id == user.id
        ).delete()
        for aid in payload.allergen_ids:
            db.add(ProfileAllergen(user_id=user.id, allergen_id=aid))

    if payload.custom_conditions is not None:
        info.custom_conditions = payload.custom_conditions
    if payload.custom_allergens is not None:
        info.custom_allergens = [item.model_dump() for item in payload.custom_allergens]

    db.commit()
    db.refresh(user)
    db.refresh(info)

    profile_out = ProfileOut.model_validate(info)
    return MeOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        staff_profile=user.staff_profile,
        profile=profile_out,
    )

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.deps import get_db, get_current_user
from app.models import User, UserProfile, UserMedicalCondition, UserAllergen, BodyMetricHistory
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
from app.services.body_metrics import latest_body_metric, upsert_body_metric
from app.services.activity_levels import get_activity_level

router = APIRouter(prefix="/auth", tags=["auth"])


def _profile_out(info: UserProfile, metric: BodyMetricHistory | None) -> ProfileOut:
    """Ghép hồ sơ ổn định với số đo cơ thể mới nhất mà không đổi hợp đồng API."""
    data = ProfileOut.model_validate(info).model_dump()
    data.update({
        "height_cm": float(metric.height_cm) if metric and metric.height_cm is not None else None,
        "weight_kg": float(metric.weight_kg) if metric and metric.weight_kg is not None else None,
        "bmi": metric.bmi if metric else None,
    })
    return ProfileOut(**data)


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

        # 2. user_profile + tính mục tiêu calo
        activity_level = get_activity_level(db, p.activity_level)
        target = daily_calorie_target(
            gender=p.gender,
            birth_date=p.birth_date,
            height_cm=p.height_cm,
            weight_kg=p.weight_kg,
            activity_multiplier=float(activity_level.calorie_multiplier),
            goal=p.goal,
        )

        info = UserProfile(
            user_id=user.id,
            full_name=payload.full_name,
            gender=p.gender,
            birth_date=p.birth_date,
            activity_level=p.activity_level,
            goal=p.goal,
            daily_calorie_target=target,
            custom_conditions=p.custom_conditions,
            custom_allergens=[item.model_dump() for item in p.custom_allergens],
            # KHÔNG set bmi — generated column
        )
        db.add(info)
        db.flush()
        db.add(BodyMetricHistory(
            user_id=user.id,
            recorded_at=date.today(),
            height_cm=p.height_cm,
            weight_kg=p.weight_kg,
        ))

        # 3. bệnh nền + dị ứng (nhiều-nhiều)
        for cid in p.condition_ids:
            db.add(UserMedicalCondition(user_id=user.id, condition_id=cid))
        for aid in p.allergen_ids:
            db.add(UserAllergen(user_id=user.id, allergen_id=aid))

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
def me(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    metric = latest_body_metric(db, user.id)
    profile_out = _profile_out(user.profile, metric) if user.profile else None
    return MeOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        staff_profile=user.staff_profile,
        role_permission=user.role_permission,
        profile=profile_out,
    )


@router.put("/me", response_model=MeOut)
def update_me(
    payload: UserProfileUpdateIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Cập nhật thông tin cá nhân + hồ sơ sức khỏe của chính mình."""
    info = user.profile
    if info is None:
        info = UserProfile(user_id=user.id)
        db.add(info)
        db.flush()

    if payload.full_name is not None:
        info.full_name = payload.full_name

    selected_activity_level = None
    if payload.activity_level is not None:
        selected_activity_level = get_activity_level(db, payload.activity_level)

    metric = latest_body_metric(db, user.id)
    if payload.height_cm is not None or payload.weight_kg is not None:
        next_height = payload.height_cm if payload.height_cm is not None else (
            float(metric.height_cm) if metric and metric.height_cm is not None else None
        )
        next_weight = payload.weight_kg if payload.weight_kg is not None else (
            float(metric.weight_kg) if metric and metric.weight_kg is not None else None
        )
        if next_height is not None and next_weight is not None:
            validate_body_metrics(float(next_height), float(next_weight))
        metric = upsert_body_metric(
            db,
            user.id,
            height_cm=payload.height_cm,
            weight_kg=payload.weight_kg,
        )

    profile_fields = ["gender", "birth_date", "activity_level", "goal"]
    changed_profile = payload.height_cm is not None or payload.weight_kg is not None
    for field in profile_fields:
        val = getattr(payload, field)
        if val is not None:
            setattr(info, field, val)
            changed_profile = True

    # Tính lại calo mục tiêu nếu hồ sơ đầy đủ và có thay đổi
    if changed_profile and all([
        info.gender, info.birth_date,
        metric and metric.height_cm, metric and metric.weight_kg,
        info.activity_level, info.goal,
    ]):
        info.daily_calorie_target = daily_calorie_target(  # type: ignore
            gender=str(info.gender),
            birth_date=info.birth_date,  # type: ignore
            height_cm=float(metric.height_cm),  # type: ignore
            weight_kg=float(metric.weight_kg),  # type: ignore
            activity_multiplier=float(
                selected_activity_level.calorie_multiplier
                if selected_activity_level is not None
                else info.activity_level_ref.calorie_multiplier
            ),
            goal=str(info.goal),
        )

    # Cập nhật bệnh nền + dị ứng nếu có gửi lên
    if payload.condition_ids is not None:
        db.query(UserMedicalCondition).filter(
            UserMedicalCondition.user_id == user.id
        ).delete()
        for cid in payload.condition_ids:
            db.add(UserMedicalCondition(user_id=user.id, condition_id=cid))

    if payload.allergen_ids is not None:
        db.query(UserAllergen).filter(
            UserAllergen.user_id == user.id
        ).delete()
        for aid in payload.allergen_ids:
            db.add(UserAllergen(user_id=user.id, allergen_id=aid))

    if payload.custom_conditions is not None:
        setattr(info, "custom_conditions", payload.custom_conditions)
    if payload.custom_allergens is not None:
        setattr(info, "custom_allergens", [item.model_dump() for item in payload.custom_allergens])

    db.commit()
    db.refresh(user)
    db.refresh(info)
    metric = latest_body_metric(db, user.id)

    profile_out = _profile_out(info, metric)
    return MeOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        staff_profile=user.staff_profile,
        role_permission=user.role_permission,
        profile=profile_out,
    )

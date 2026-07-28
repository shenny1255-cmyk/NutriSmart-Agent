from datetime import date, timedelta
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.deps import get_db, get_current_user
from app.models import User, ActivityLog, MealLog, Food, Exercise, BodyMetricHistory
from app.schemas import (
    DailySummaryOut, ActivityIn, TodayActivityOut,
    ManualMealIn, MealLogOut, ManualActivityIn, ActivityLogOut, WeightIn, WeightOut,
)
from app.services.calorie import calories_burned

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tracking", tags=["tracking"])


@router.get("/summary", response_model=list[DailySummaryOut])
def summary(
    days: int = 7,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    sql = text("""
        SELECT day, kcal_intake, kcal_burned,
               daily_calorie_target, kcal_remaining
        FROM v_daily_summary
        WHERE user_id = :uid AND day >= :since
        ORDER BY day
    """)
    since = date.today() - timedelta(days=days - 1)
    rows = db.execute(sql, {"uid": str(user.id), "since": since}).mappings().all()
    return list(rows)


@router.post("/daily-activity", response_model=TodayActivityOut)
def upsert_daily_activity(
    payload: ActivityIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Mobile gửi số bước + calo tiêu hao lên. UPSERT theo (user_id, log_date)."""
    try:
        log_date = payload.log_date or date.today()

        # Tìm bản ghi hiện có cho ngày hôm đó (exercise_id IS NULL -> log từ Mobile)
        existing = (
            db.query(ActivityLog)
            .filter(
                ActivityLog.user_id == user.id,
                ActivityLog.log_date == log_date,
                ActivityLog.exercise_id.is_(None)
            )
            .first()
        )

        if existing:
            existing.steps = payload.steps
            existing.calories_burned = payload.calories_burned
        else:
            existing = ActivityLog(
                user_id=user.id,
                steps=payload.steps,
                calories_burned=payload.calories_burned,
                log_date=log_date,
            )
            db.add(existing)

        db.commit()
        db.refresh(existing)

        return TodayActivityOut(
            steps=existing.steps or 0,
            calories_burned=float(existing.calories_burned or 0),
            distance_km=payload.distance_km,
            log_date=existing.log_date,
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Lỗi upsert_daily_activity: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/today-activity", response_model=TodayActivityOut)
def get_today_activity(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Web Dashboard gọi để lấy số bước + calo tiêu hao hôm nay từ Mobile."""
    today = date.today()
    log = (
        db.query(ActivityLog)
        .filter(
            ActivityLog.user_id == user.id,
            ActivityLog.log_date == today,
            ActivityLog.exercise_id.is_(None)
        )
        .first()
    )

    return TodayActivityOut(
        steps=log.steps if log else 0,
        calories_burned=float(log.calories_burned) if log else 0.0,
        distance_km=0.0,
        log_date=today,
    )


# ---------- Nhật ký bữa ăn thủ công ----------
# Các hàm dưới nhận (db, user) trực tiếp để test gọi được mà không cần dựng HTTP.

def them_bua_an(db: Session, user: User, payload: ManualMealIn) -> MealLogOut:
    """Ghi một bữa ăn. Chọn món có sẵn hoặc gõ tên món mới (món mới được thêm vào danh mục)."""
    log_date = payload.log_date or date.today()

    food = None
    if payload.food_id:
        food = db.query(Food).filter(Food.id == payload.food_id).first()
        if not food:
            raise HTTPException(404, "Không tìm thấy món ăn")
    elif payload.food_name:
        ten = payload.food_name.strip()
        # Trùng tên thì dùng lại, tránh phình bảng foods mỗi lần ghi nhật ký
        food = db.query(Food).filter(Food.name.ilike(ten)).first()
        if not food:
            if payload.calories_kcal is None:
                raise HTTPException(400, "Món mới cần nhập số calo")
            food = Food(
                name=ten,
                calories_kcal=payload.calories_kcal,
                protein_g=payload.protein_g,
                carb_g=payload.carb_g,
                fat_g=payload.fat_g,
                source="Người dùng nhập",
            )
            db.add(food)
            db.flush()
    else:
        raise HTTPException(400, "Chọn món có sẵn hoặc nhập tên món")

    kcal_moi_phan = payload.calories_kcal if payload.calories_kcal is not None else float(food.calories_kcal)
    tong_kcal = round(kcal_moi_phan * payload.quantity, 2)

    log = MealLog(
        user_id=user.id,
        food_id=food.id,
        meal_type=payload.meal_type,
        quantity=payload.quantity,
        calories_kcal=tong_kcal,
        log_date=log_date,
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    return MealLogOut(
        id=log.id, food_name=food.name, meal_type=log.meal_type,
        quantity=float(log.quantity), calories_kcal=float(log.calories_kcal),
        log_date=log.log_date,
    )


def danh_sach_bua_an(db: Session, user: User, ngay: date) -> list[MealLogOut]:
    rows = (
        db.query(MealLog, Food.name)
        .outerjoin(Food, Food.id == MealLog.food_id)  # type: ignore
        .filter(MealLog.user_id == user.id, MealLog.log_date == ngay)  # type: ignore
        .order_by(MealLog.logged_at)
        .all()
    )
    return [
        MealLogOut(
            id=m.id, food_name=ten or "Món không rõ", meal_type=m.meal_type,
            quantity=float(m.quantity), calories_kcal=float(m.calories_kcal),
            log_date=m.log_date,
        )
        for m, ten in rows
    ]


def xoa_bua_an(db: Session, user: User, log_id: int) -> None:
    log = (
        db.query(MealLog)
        .filter(MealLog.id == log_id, MealLog.user_id == user.id)  # type: ignore
        .first()
    )
    if not log:
        raise HTTPException(404, "Không tìm thấy bữa ăn trong nhật ký")
    db.delete(log)
    db.commit()


@router.post("/meals", response_model=MealLogOut)
def api_them_bua_an(
    payload: ManualMealIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return them_bua_an(db, user, payload)


@router.get("/meals", response_model=list[MealLogOut])
def api_danh_sach_bua_an(
    d: date | None = Query(None, description="Ngày cần xem, mặc định hôm nay"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return danh_sach_bua_an(db, user, d or date.today())


@router.delete("/meals/{log_id}", status_code=204)
def api_xoa_bua_an(
    log_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    xoa_bua_an(db, user, log_id)


# ---------- Nhật ký vận động thủ công ----------

def them_van_dong(db: Session, user: User, payload: ManualActivityIn) -> ActivityLogOut:
    """Ghi một buổi tập. Không nhập calo thì tự tính theo MET × cân nặng × số phút."""
    bai_tap = db.query(Exercise).filter(Exercise.id == payload.exercise_id).first()
    if not bai_tap:
        raise HTTPException(404, "Không tìm thấy bài tập")

    kcal = payload.calories_burned
    if kcal is None:
        can_nang = user.profile.weight_kg if user.profile else None
        kcal = calories_burned(bai_tap.met_value, can_nang, payload.duration_min)

    log = ActivityLog(
        user_id=user.id,
        exercise_id=bai_tap.id,
        steps=payload.steps,
        duration_min=payload.duration_min,
        calories_burned=kcal,
        log_date=payload.log_date or date.today(),
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    return ActivityLogOut(
        id=log.id, exercise_name=bai_tap.name, duration_min=log.duration_min or 0,
        calories_burned=float(log.calories_burned or 0), steps=log.steps or 0,
        log_date=log.log_date,
    )


def danh_sach_van_dong(db: Session, user: User, ngay: date) -> list[ActivityLogOut]:
    rows = (
        db.query(ActivityLog, Exercise.name)
        .outerjoin(Exercise, Exercise.id == ActivityLog.exercise_id)  # type: ignore
        .filter(ActivityLog.user_id == user.id, ActivityLog.log_date == ngay,  # type: ignore
                ActivityLog.exercise_id.isnot(None))
        .order_by(ActivityLog.id)
        .all()
    )
    return [
        ActivityLogOut(
            id=a.id, exercise_name=ten or "Vận động", duration_min=a.duration_min or 0,
            calories_burned=float(a.calories_burned or 0), steps=a.steps or 0,
            log_date=a.log_date,
        )
        for a, ten in rows
    ]


def xoa_van_dong(db: Session, user: User, log_id: int) -> None:
    log = (
        db.query(ActivityLog)
        .filter(ActivityLog.id == log_id, ActivityLog.user_id == user.id)  # type: ignore
        .first()
    )
    if not log:
        raise HTTPException(404, "Không tìm thấy buổi tập trong nhật ký")
    db.delete(log)
    db.commit()


@router.post("/activities", response_model=ActivityLogOut)
def api_them_van_dong(
    payload: ManualActivityIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return them_van_dong(db, user, payload)


@router.get("/activities", response_model=list[ActivityLogOut])
def api_danh_sach_van_dong(
    d: date | None = Query(None, description="Ngày cần xem, mặc định hôm nay"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return danh_sach_van_dong(db, user, d or date.today())


@router.delete("/activities/{log_id}", status_code=204)
def api_xoa_van_dong(
    log_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    xoa_van_dong(db, user, log_id)


# ---------- Cân nặng ----------

def cap_nhat_can_nang(db: Session, user: User, payload: WeightIn) -> WeightOut:
    """Cập nhật cân nặng hiện tại + ghi mốc lịch sử (mỗi ngày 1 bản ghi).

    Mục tiêu calo KHÔNG đổi ở đây: nó do lộ trình quản lý và được hiệu chỉnh
    sau mỗi chu kỳ đánh giá 7 ngày (xem services/plan_evaluator.py).
    """
    if not user.profile:
        raise HTTPException(400, "Chưa có hồ sơ sức khỏe")

    ngay = payload.recorded_at or date.today()

    # Chỉ cân nặng mới nhất mới cập nhật vào hồ sơ (BMI là cột generated, tự tính)
    if ngay >= date.today():
        user.profile.weight_kg = payload.weight_kg

    row = (
        db.query(BodyMetricHistory)
        .filter(BodyMetricHistory.user_id == user.id,  # type: ignore
                BodyMetricHistory.recorded_at == ngay)
        .first()
    )
    chieu_cao = float(user.profile.height_cm) if user.profile.height_cm else None
    bmi = round(payload.weight_kg / ((chieu_cao / 100) ** 2), 2) if chieu_cao else None

    if row:
        row.weight_kg = payload.weight_kg
        row.bmi = bmi
    else:
        row = BodyMetricHistory(user_id=user.id, recorded_at=ngay,
                                weight_kg=payload.weight_kg, bmi=bmi)
        db.add(row)

    db.commit()
    db.refresh(row)
    db.refresh(user.profile)
    return WeightOut(recorded_at=row.recorded_at, weight_kg=float(row.weight_kg),
                     bmi=float(row.bmi) if row.bmi is not None else None)


def lich_su_can_nang(db: Session, user: User, days: int = 90) -> list[WeightOut]:
    tu_ngay = date.today() - timedelta(days=days)
    rows = (
        db.query(BodyMetricHistory)
        .filter(BodyMetricHistory.user_id == user.id,  # type: ignore
                BodyMetricHistory.recorded_at >= tu_ngay)
        .order_by(BodyMetricHistory.recorded_at)
        .all()
    )
    return [
        WeightOut(recorded_at=r.recorded_at, weight_kg=float(r.weight_kg),
                  bmi=float(r.bmi) if r.bmi is not None else None)
        for r in rows if r.weight_kg is not None
    ]


@router.put("/weight", response_model=WeightOut)
def api_cap_nhat_can_nang(
    payload: WeightIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return cap_nhat_can_nang(db, user, payload)


@router.get("/weight", response_model=list[WeightOut])
def api_lich_su_can_nang(
    days: int = Query(90, ge=7, le=365),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return lich_su_can_nang(db, user, days)
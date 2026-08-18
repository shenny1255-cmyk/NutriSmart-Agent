from datetime import date, datetime, timedelta
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
from app.services.calorie import calories_burned, manual_calories_limit
from app.services.body_metrics import latest_body_metric, upsert_body_metric

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tracking", tags=["tracking"])


def _ngay_viet_nam(column):
    """Đổi TIMESTAMPTZ sang ngày Việt Nam trước khi lọc theo lịch địa phương."""
    from sqlalchemy import func
    return func.date(func.timezone("Asia/Bangkok", column))


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
    rows = [dict(r) for r in db.execute(sql, {"uid": str(user.id), "since": since}).mappings().all()]
    today = date.today()
    if not any(r["day"] == today for r in rows):
        target = (user.profile.daily_calorie_target if user.profile else None) or 2000
        rows.append({
            "day": today,
            "kcal_intake": 0.0,
            "kcal_burned": 0.0,
            "daily_calorie_target": target,
            "kcal_remaining": float(target),
        })
        rows.sort(key=lambda x: x["day"])
    return rows


@router.post("/daily-activity", response_model=TodayActivityOut)
def upsert_daily_activity(
    payload: ActivityIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Mobile gửi số bước + calo tiêu hao lên. UPSERT theo (user_id, date)."""
    try:
        from sqlalchemy import func
        log_date = payload.log_date or date.today()

        # Tìm bản ghi hiện có cho ngày hôm đó (exercise_id IS NULL -> log từ Mobile)
        existing = (
            db.query(ActivityLog)
            .filter(
                ActivityLog.user_id == user.id,  # type: ignore
                _ngay_viet_nam(func.coalesce(ActivityLog.started_at, ActivityLog.logged_at)) == log_date,  # type: ignore
                ActivityLog.exercise_id.is_(None)  # type: ignore
            )
            .first()
        )

        if existing:
            existing.steps = payload.steps  # type: ignore
            existing.calories_burned = payload.calories_burned  # type: ignore
        else:
            existing = ActivityLog(
                user_id=user.id,
                steps=payload.steps,
                calories_burned=payload.calories_burned,
            )
            db.add(existing)

        db.commit()
        db.refresh(existing)

        return TodayActivityOut(
            steps=int(existing.steps or 0),  # type: ignore
            calories_burned=float(existing.calories_burned or 0),  # type: ignore
            distance_km=payload.distance_km,
            log_date=log_date,
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
    from sqlalchemy import func
    today = date.today()
    log = (
        db.query(ActivityLog)
        .filter(
            ActivityLog.user_id == user.id,  # type: ignore
            _ngay_viet_nam(func.coalesce(ActivityLog.started_at, ActivityLog.logged_at)) == today,  # type: ignore
            ActivityLog.exercise_id.is_(None)  # type: ignore
        )
        .first()
    )

    return TodayActivityOut(
        steps=int(log.steps) if log and log.steps else 0,  # type: ignore
        calories_burned=float(log.calories_burned) if log and log.calories_burned else 0.0,  # type: ignore
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
        food = db.query(Food).filter(Food.id == payload.food_id).first()  # type: ignore
        if not food:
            raise HTTPException(404, "Không tìm thấy món ăn")
    elif payload.food_name:
        ten = payload.food_name.strip()
        # Trùng tên thì dùng lại, tránh phình bảng foods mỗi lần ghi nhật ký
        food = db.query(Food).filter(Food.name.ilike(ten)).first()  # type: ignore
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
        id=int(log.id), food_name=str(food.name), meal_type=str(log.meal_type),  # type: ignore
        quantity=float(log.quantity), calories_kcal=float(log.calories_kcal),
        log_date=log.log_date,  # type: ignore
    )


def danh_sach_bua_an(db: Session, user: User, ngay: date) -> list[MealLogOut]:
    rows = (
        db.query(MealLog, Food.name)  # type: ignore
        .outerjoin(Food, Food.id == MealLog.food_id)  # type: ignore
        .filter(MealLog.user_id == user.id, MealLog.log_date == ngay)  # type: ignore
        .order_by(MealLog.logged_at)
        .all()
    )
    return [
        MealLogOut(
            id=int(m.id), food_name=str(ten) if ten else "Món không rõ", meal_type=str(m.meal_type),  # type: ignore
            quantity=float(m.quantity), calories_kcal=float(m.calories_kcal),
            log_date=m.log_date,  # type: ignore
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
    bai_tap = db.query(Exercise).filter(Exercise.id == payload.exercise_id).first()  # type: ignore
    if not bai_tap:
        raise HTTPException(404, "Không tìm thấy bài tập")

    metric = latest_body_metric(db, user.id)
    can_nang = metric.weight_kg if metric else None
    kcal_du_kien, kcal_toi_da = manual_calories_limit(
        float(bai_tap.met_value), float(can_nang) if can_nang else None, payload.duration_min  # type: ignore
    )
    kcal = payload.calories_burned
    if kcal is None:
        kcal = kcal_du_kien
        if kcal <= 0:
            raise HTTPException(
                422,
                "Không thể tự tính kcal. Vui lòng cập nhật cân nặng hoặc tự nhập kcal lớn hơn 0.",
            )
    elif kcal > kcal_toi_da:
        du_kien = f" khoảng {round(kcal_du_kien)} kcal" if kcal_du_kien > 0 else ""
        raise HTTPException(
            422,
            f"Kcal nhập vào quá cao so với bài tập và thời gian. Hệ thống ước tính{du_kien}.",
        )

    started_at = payload.started_at or datetime.now().astimezone()
    ended_at = payload.ended_at

    log = ActivityLog(
        user_id=user.id,
        exercise_id=bai_tap.id,
        steps=payload.steps,
        duration_min=payload.duration_min,
        calories_burned=kcal,
        started_at=started_at,
        ended_at=ended_at,
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    return ActivityLogOut(
        id=int(log.id), exercise_name=str(bai_tap.name), duration_min=int(log.duration_min or 0),  # type: ignore
        calories_burned=float(log.calories_burned or 0), steps=int(log.steps or 0),  # type: ignore
        started_at=log.started_at, ended_at=log.ended_at, logged_at=log.logged_at,  # type: ignore
    )


def danh_sach_van_dong(db: Session, user: User, ngay: date) -> list[ActivityLogOut]:
    from sqlalchemy import func
    rows = (
        db.query(ActivityLog, Exercise.name)  # type: ignore
        .outerjoin(Exercise, Exercise.id == ActivityLog.exercise_id)  # type: ignore
        .filter(
            ActivityLog.user_id == user.id,
            _ngay_viet_nam(func.coalesce(ActivityLog.started_at, ActivityLog.logged_at)) == ngay,
            ActivityLog.exercise_id.isnot(None)
        )
        .order_by(ActivityLog.id)  # type: ignore
        .all()
    )
    return [
        ActivityLogOut(
            id=int(a.id), exercise_name=str(ten) if ten else "Vận động", duration_min=int(a.duration_min or 0),  # type: ignore
            calories_burned=float(a.calories_burned or 0), steps=int(a.steps or 0),  # type: ignore
            started_at=a.started_at, ended_at=a.ended_at, logged_at=a.logged_at,  # type: ignore
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
    """Cập nhật cân nặng trong bảng lịch sử (mỗi ngày một bản ghi).

    Mục tiêu calo KHÔNG đổi ở đây: nó do lộ trình quản lý và được hiệu chỉnh
    sau mỗi chu kỳ check-in 14 ngày (xem services/plan_checkin.py).
    """
    if not user.profile:
        raise HTTPException(400, "Chưa có hồ sơ sức khỏe")

    ngay = payload.recorded_at or date.today()

    row = upsert_body_metric(
        db,
        user.id,
        weight_kg=payload.weight_kg,
        recorded_at=ngay,
    )

    db.commit()
    db.refresh(row)
    return WeightOut(
        recorded_at=row.recorded_at,  # type: ignore
        weight_kg=float(row.weight_kg) if row.weight_kg is not None else 0.0,  # type: ignore
        bmi=row.bmi,
    )


def lich_su_can_nang(db: Session, user: User, days: int = 90) -> list[WeightOut]:
    tu_ngay = date.today() - timedelta(days=days)
    rows = (
        db.query(BodyMetricHistory)
        .filter(BodyMetricHistory.user_id == user.id, BodyMetricHistory.recorded_at >= tu_ngay)  # type: ignore
        .order_by(BodyMetricHistory.recorded_at)  # type: ignore
        .all()
    )
    return [
        WeightOut(
            recorded_at=r.recorded_at,  # type: ignore
            weight_kg=float(r.weight_kg) if r.weight_kg is not None else 0.0,  # type: ignore
            bmi=r.bmi,
        )
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

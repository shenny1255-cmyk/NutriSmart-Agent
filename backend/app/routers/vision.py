from datetime import date
import logging
import time

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.deps import get_db, get_current_user
from app.models import User, Food, MealLog
from app.schemas import MealAnalyzeOut, MealLogIn
from app.services.gemini_vision import analyze_food_image
from app.services import guardrails
from app.services.llm import _audit_external_call
from app.services.plan_progress import sync_meal_log_with_plan

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/vision", tags=["vision"])


def _audit_vision(user, nbytes: int, t0: float, ok: bool, error: str | None = None) -> None:
    """Mỗi ảnh gửi ra Gemini đều ghi audit như lời gọi chat (không gửi kèm hồ sơ nên không có gì để ẩn danh)."""
    _audit_external_call(actor_id=user.id, provider="gemini", model=None, purpose="meal_scan",
                         chars_sent=0, redactions={}, latency_ms=int((time.perf_counter() - t0) * 1000),
                         ok=ok, error=error, extra={"bytes_sent": nbytes})


@router.post("/analyze-meal", response_model=MealAnalyzeOut)
async def analyze_meal_image(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Nhận file ảnh tải lên từ Mobile/Web, gọi Gemini Flash 2.0 phân tích dinh dưỡng đĩa thức ăn.
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File tải lên phải là định dạng hình ảnh (JPEG, PNG, WEBP...)"
        )

    # Ảnh luôn được phân tích bằng Gemini (không có model Vision nội bộ). Người dùng đã từ chối
    # gửi dữ liệu ra AI đám mây thì KHÔNG gửi ảnh, kể cả khi ảnh không kèm hồ sơ sức khỏe.
    if user.profile is not None and user.profile.ai_local_only:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=("Bạn đang chọn chỉ xử lý bằng AI nội bộ, còn phân tích ảnh cần gửi ảnh tới AI đám mây "
                    "(Google Gemini). Bạn có thể đổi lựa chọn trong Hồ sơ > Quyền riêng tư và AI, "
                    "hoặc ghi món vào Nhật ký thủ công."),
        )

    contents = await file.read()
    t0 = time.perf_counter()
    try:
        analysis_result = analyze_food_image(contents, mime_type=file.content_type or "image/jpeg")
    except Exception as e:
        _audit_vision(user, len(contents), t0, ok=False, error=type(e).__name__)
        logger.error(f"Lỗi phân tích hình ảnh món ăn: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Dịch vụ phân tích ảnh tạm thời không khả dụng. Vui lòng thử lại sau."
        )

    _audit_vision(user, len(contents), t0, ok=True)

    # Guardrail chạy SAU Vision: độ tin cậy, dị ứng/bệnh nền, vượt chỉ tiêu ngày.
    # Lỗi ở bước này không được làm mất kết quả phân tích.
    try:
        consumed_today = float(
            db.query(func.coalesce(func.sum(MealLog.calories_kcal), 0))
            .filter(MealLog.user_id == user.id, MealLog.log_date == date.today())  # type: ignore
            .scalar()
        )
        analysis_result["warnings"] = guardrails.check_meal_scan(
            analysis_result, guardrails.profile_from_user(user), consumed_today
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("Không chạy được Warning Engine cho ảnh món ăn: %s", e)
    return MealAnalyzeOut(**analysis_result)


@router.post("/log-meal")
def log_meal(
    payload: MealLogIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Lưu bữa ăn đã phân tích vào CSDL (bảng foods & meal_logs).
    Sau khi lưu, card 'ĐÃ NẠP' trên Web & Mobile tự động cộng dồn
    và tự động tick mục tương ứng trong Lộ trình hôm nay.
    """
    try:
        log_date = payload.log_date or date.today()

        # 1. Tạo bản ghi món ăn trong bảng foods
        food = Food(
            name=payload.food_name,
            calories_kcal=payload.calories_kcal,
            protein_g=payload.protein_g,
            carb_g=payload.carb_g,
            fat_g=payload.fat_g,
            source="AI Gemini Flash",
        )
        db.add(food)
        db.flush()  # Lấy food.id

        # 2. Tạo nhật ký bữa ăn trong bảng meal_logs
        total_calories = payload.calories_kcal * payload.quantity
        meal_log = MealLog(
            user_id=user.id,
            food_id=food.id,
            meal_type=payload.meal_type,
            quantity=payload.quantity,
            calories_kcal=total_calories,
            log_date=log_date,
            source_type="VISION",
            item_name_snapshot=payload.food_name,
        )
        db.add(meal_log)
        db.flush()

        # 3. Tự động đồng bộ với Lộ trình (Plan) nếu có
        plan_sync = sync_meal_log_with_plan(db, user, meal_log, log_date)
        db.commit()

        # 4. Tính tổng Calo đã nạp trong ngày hôm nay của User
        total_today = (
            db.query(func.coalesce(func.sum(MealLog.calories_kcal), 0))
            .filter(MealLog.user_id == user.id, MealLog.log_date == log_date)  # type: ignore
            .scalar()
        )

        return {
            "status": "success",
            "message": f"Đã ghi nhận {payload.food_name} (+{total_calories} kcal)",
            "logged_food": payload.food_name,
            "added_calories": total_calories,
            "total_intake_today": float(total_today),
            "log_date": str(log_date),
            "plan_synced": plan_sync,
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Lỗi lưu bữa ăn: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi lưu bữa ăn vào CSDL: {str(e)}"
        )

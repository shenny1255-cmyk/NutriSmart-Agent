from datetime import date
import logging

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.deps import get_db, get_current_user
from app.models import User, Food, MealLog
from app.schemas import MealAnalyzeOut, MealLogIn
from app.services.gemini_vision import analyze_food_image

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/vision", tags=["vision"])


@router.post("/analyze-meal", response_model=MealAnalyzeOut)
async def analyze_meal_image(
    file: UploadFile = File(...),
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

    try:
        contents = await file.read()
        analysis_result = analyze_food_image(contents, mime_type=file.content_type or "image/jpeg")
        return MealAnalyzeOut(**analysis_result)
    except Exception as e:
        logger.error(f"Lỗi phân tích hình ảnh món ăn: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Dịch vụ phân tích ảnh tạm thời không khả dụng. Vui lòng thử lại sau."
        )


@router.post("/log-meal")
def log_meal(
    payload: MealLogIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Lưu bữa ăn đã phân tích vào CSDL (bảng foods & meal_logs).
    Sau khi lưu, card 'ĐÃ NẠP' trên Web & Mobile tự động cộng dồn.
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
        )
        db.add(meal_log)
        db.commit()

        # 3. Tính tổng Calo đã nạp trong ngày hôm nay của User
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
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Lỗi lưu bữa ăn: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi lưu bữa ăn vào CSDL: {str(e)}"
        )

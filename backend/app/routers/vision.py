from datetime import date, datetime, timezone
import logging
import time

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.deps import get_db, get_current_user
from app.models import User, Food, MealLog, VisionFeedback
from app.schemas import MealAnalyzeOut, MealLogIn
from app.services.gemini_vision import analyze_food_image, refine_components
from app.services import few_shot, guardrails, portion
from app.services.llm import _audit_external_call
from app.services.plan_progress import sync_meal_log_with_plan

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/vision", tags=["vision"])


def _audit_vision(user, nbytes: int, t0: float, ok: bool, error: str | None = None,
                  purpose: str = "meal_scan") -> None:
    """Mỗi ảnh gửi ra Gemini đều ghi audit như lời gọi chat (không gửi kèm hồ sơ nên không có gì để ẩn danh)."""
    _audit_external_call(actor_id=user.id, provider="gemini", model=None, purpose=purpose,
                         chars_sent=0, redactions={}, latency_ms=int((time.perf_counter() - t0) * 1000),
                         ok=ok, error=error, extra={"bytes_sent": nbytes})


def _apply_few_shot(db: Session, user: User, image: bytes, mime_type: str, analysis: dict) -> dict:
    """Tinh chỉnh gram bằng ca Expert đã duyệt. Lỗi ở đây luôn giữ nguyên kết quả lượt đầu."""
    if not portion.build_components(analysis.get("components")):
        return analysis
    examples = few_shot.retrieve(db, analysis.get("food_name"))
    if not examples:
        return analysis
    t0 = time.perf_counter()
    try:
        refined = refine_components(image, mime_type, analysis, few_shot.prompt_examples(examples))
    except Exception as e:  # noqa: BLE001
        _audit_vision(user, len(image), t0, ok=False, error=type(e).__name__, purpose="meal_scan_refine")
        logger.warning("Không tinh chỉnh được bằng few-shot: %s", e)
        return analysis
    _audit_vision(user, len(image), t0, ok=True, purpose="meal_scan_refine")
    merged = portion.merge_refined_grams(analysis["components"], refined)
    if merged is None:
        return analysis
    return {**analysis, "components": merged, "few_shot_ids": [str(e.id) for e in examples]}


def _save_prediction(db: Session, user: User, analysis: dict):
    """Ghi dự đoán để so với số người dùng chốt. Lỗi ghi log không được làm mất kết quả phân tích."""
    if not analysis.get("components"):
        return None
    try:
        row = VisionFeedback(
            user_id=user.id, food_name=analysis["food_name"], ai_total_kcal=analysis.get("ai_total_kcal"),
            predicted_kcal=analysis["calories_kcal"], predicted_components=analysis["components"],
            few_shot_ids=analysis.get("few_shot_ids") or [],
        )
        db.add(row)
        db.commit()
        return row.id
    except Exception as e:  # noqa: BLE001
        db.rollback()
        logger.warning("Không ghi được dự đoán khẩu phần: %s", e)
        return None


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
    analysis_result = _apply_few_shot(db, user, contents, file.content_type or "image/jpeg", analysis_result)
    analysis_result = portion.enrich(analysis_result)
    analysis_result["few_shot_used"] = len(analysis_result.get("few_shot_ids") or [])
    analysis_result["scan_id"] = _save_prediction(db, user, analysis_result)

    # Guardrail chạy SAU Vision: độ tin cậy, dị ứng/bệnh nền, vượt chỉ tiêu ngày.
    # Lỗi ở bước này không được làm mất kết quả phân tích.
    try:
        consumed_today = float(
            db.query(func.coalesce(func.sum(MealLog.calories_kcal), 0))
            .filter(MealLog.user_id == user.id, MealLog.log_date == date.today())  # type: ignore
            .scalar()
        )
        names = ", ".join(c["name"] for c in analysis_result["components"])
        guard_input = {**analysis_result, "description": f"{analysis_result.get('description') or ''} . {names}"}
        analysis_result["warnings"] = guardrails.check_meal_scan(
            guard_input, guardrails.profile_from_user(user), consumed_today
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
    scan, final_components = None, None
    if payload.scan_id is not None and payload.components:
        scan = db.get(VisionFeedback, payload.scan_id)
        if scan is None or scan.user_id != user.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy lần phân tích ảnh này")
        if scan.status != "PREDICTED":
            raise HTTPException(status.HTTP_409_CONFLICT, "Lần phân tích này đã được lưu vào nhật ký")
        try:
            final_components = portion.recalculate(
                [item.model_dump() for item in payload.components], scan.predicted_components)
        except ValueError as e:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(e))
        sums = portion.totals(final_components)
        payload = payload.model_copy(update={
            "calories_kcal": sums["energy_kcal"], "protein_g": sums["protein_g"], "carb_g": sums["carb_g"],
            "fat_g": sums["fat_g"], "quantity": 1.0,
        })

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

        if scan is not None:
            corrected = portion.was_corrected(scan.predicted_components, final_components)
            scan.status = "CORRECTED" if corrected else "CONFIRMED"
            scan.final_components = final_components
            scan.final_kcal = total_calories
            scan.meal_log_id = meal_log.id
            scan.confirmed_at = datetime.now(timezone.utc)

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

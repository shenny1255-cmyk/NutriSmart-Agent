"""Sinh lộ trình dinh dưỡng bằng LLM (gemma3 qua Ollama).

Tách khỏi router để luồng check-in 14 ngày dùng lại cùng một đường sinh thực đơn:
profile + bệnh nền + dị ứng + calo mục tiêu.
"""
import json
import logging
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.config import settings
from app.models import User, NutritionPlan, BodyMetricHistory
from app.services import ollama_client
from app.services.nutrition_context import gather_context

logger = logging.getLogger(__name__)

PLAN_DAYS = 7
PLAN_VALID_DAYS = 14


def build_prompt(profile_data: dict, target: int, note: str | None = None) -> str:
    """Prompt tiếng Việt, ép LLM trả về đúng một chuỗi JSON."""
    conditions = ", ".join(profile_data.get("conditions") or []) or "không có"
    allergens = ", ".join(profile_data.get("allergens") or []) or "không có"

    extra = ""
    if note:
        extra = (
            "\nĐIỀU CHỈNH TỪ KỲ ĐÁNH GIÁ TRƯỚC (BẮT BUỘC TUÂN THỦ):\n"
            f"{note}\n"
        )

    return f"""Bạn là một chuyên gia dinh dưỡng. Hãy tạo một lộ trình ăn uống và tập luyện {PLAN_DAYS} ngày cho người dùng sau:
- Giới tính: {profile_data.get('gender')}
- Tuổi: {profile_data.get('age')}
- Chiều cao: {profile_data.get('height_cm')} cm
- Cân nặng: {profile_data.get('weight_kg')} kg
- BMI: {profile_data.get('bmi')}
- Mục tiêu: {profile_data.get('goal')}
- Lượng calo mục tiêu mỗi ngày: {target} kcal
- Bệnh nền: {conditions}
- Dị ứng: {allergens}
{extra}
YÊU CẦU BẮT BUỘC:
1. AN TOÀN SỨC KHỎE: TUYỆT ĐỐI không dùng nguyên liệu người dùng dị ứng ({allergens}).
   Món ăn phải phù hợp với bệnh nền ({conditions}) — ví dụ tiểu đường thì hạn chế đường và
   tinh bột hấp thu nhanh, tăng huyết áp thì giảm muối, gout thì tránh nội tạng và hải sản.
2. ĐA DẠNG MÓN ĂN: Các món Sáng/Trưa/Tối phải cực kỳ phong phú, ưu tiên món ăn Việt Nam thực tế, đổi mới liên tục qua {PLAN_DAYS} ngày (không lặp đi lặp lại).
3. ĐA DẠNG BÀI TẬP: Đề xuất bài tập thể dục thay đổi mỗi ngày (ví dụ: chạy bộ, gym, yoga, HIIT, bơi lội...).
4. ĐỊNH DẠNG CHUẨN: Trả về KẾT QUẢ ĐẦU RA LÀ ĐÚNG MỘT CHUỖI JSON DUY NHẤT. KHÔNG kèm theo bất kỳ văn bản giải thích nào khác. Đảm bảo cấu trúc JSON như sau:
{{
  "days": [
    {{
      "meals": [
        {{"type": "Sáng", "name": "Tên món ăn chi tiết", "kcal": số_nguyên}},
        {{"type": "Trưa", "name": "Tên món ăn chi tiết", "kcal": số_nguyên}},
        {{"type": "Tối", "name": "Tên món ăn chi tiết", "kcal": số_nguyên}}
      ],
      "exercise": "Mô tả bài tập chi tiết (vd: Chạy bộ - 30 phút - đốt 300 kcal)"
    }}
  ]
}}
Lưu ý: Mảng "days" phải có đúng {PLAN_DAYS} phần tử ({PLAN_DAYS} ngày). Tổng kcal mỗi ngày phải xấp xỉ {target} kcal. Tuyệt đối KHÔNG có markdown, KHÔNG có text bên ngoài JSON.
"""


def _strip_fence(reply: str) -> str:
    """Cắt bỏ ```json ... ``` nếu LLM lỡ bọc markdown."""
    reply = reply.strip()
    if reply.startswith("```json"):
        reply = reply[7:]
    if reply.startswith("```"):
        reply = reply[3:]
    if reply.endswith("```"):
        reply = reply[:-3]
    return reply.strip()


def _llm_days(prompt: str, timeout: float | None = None) -> list | None:
    """Gọi LLM và trả về mảng days; None nếu lỗi hoặc JSON không hợp lệ."""
    try:
        content = json.loads(_strip_fence(
            ollama_client.chat(
                [{"role": "user", "content": prompt}],
                model=settings.OLLAMA_MODEL,
                timeout=timeout or settings.PLAN_LLM_TIMEOUT_SECONDS,
                # JSON 7 ngày dài hơn nhiều so với 1 câu trả lời chat → nới cửa sổ sinh,
                # temperature thấp cho JSON ổn định
                options={"num_ctx": 4096, "num_predict": 2048, "temperature": 0.4},
            )
        ))
        days = content.get("days")
        if not isinstance(days, list) or not days:
            raise ValueError("Thiếu mảng 'days' trong JSON")
        return days
    except Exception as e:
        logger.warning("Lỗi khi sinh lộ trình bằng AI: %s. Dùng dữ liệu mẫu.", e)
        return None


def fallback_content(target: int) -> dict:
    """Thực đơn mẫu khi Ollama chết/timeout — trang Lộ trình vẫn có dữ liệu để hiển thị."""
    return {
        "days": [
            {
                "meals": [
                    {"type": "Sáng", "name": "Phở bò (Mẫu)", "kcal": int(target * 0.3)},
                    {"type": "Trưa", "name": "Cơm gà (Mẫu)", "kcal": int(target * 0.4)},
                    {"type": "Tối", "name": "Salad (Mẫu)", "kcal": int(target * 0.3)},
                ],
                "exercise": "Đi bộ 30 phút",
            }
            for _ in range(PLAN_DAYS)
        ]
    }


def generate_content(db: Session, user: User, target: int, note: str | None = None) -> tuple[dict, str]:
    """Trả về (content JSON, tên nguồn sinh) — có fallback khi LLM lỗi."""
    ctx = gather_context(db, user)
    profile_data = ctx.get("profile") or {}

    days = _llm_days(build_prompt(profile_data, target, note))
    if days is None:
        return fallback_content(target), "fallback-template"
    return {"days": days}, f"ai-{settings.OLLAMA_MODEL}"


def record_weight_snapshot(db: Session, user: User) -> None:
    """Ghi mốc cân nặng hôm nay (mỗi ngày 1 bản ghi) để kỳ sau tính được biến thiên."""
    info = user.info
    if not info or info.weight_kg is None:
        return

    today = date.today()
    row = (
        db.query(BodyMetricHistory)
        .filter(BodyMetricHistory.user_id == user.id, BodyMetricHistory.recorded_at == today)  # type: ignore
        .first()
    )
    if row:
        row.weight_kg = info.weight_kg  # type: ignore
    else:
        db.add(BodyMetricHistory(
            user_id=user.id,
            recorded_at=today,
            weight_kg=info.weight_kg,
        ))


def create_plan(
    db: Session,
    user: User,
    target: int | None = None,
    note: str | None = None,
    old_status: str = "REVISED",
) -> NutritionPlan:
    """Sinh lộ trình mới version+1 và hạ lộ trình đang chạy xuống old_status.

    Không commit — caller quyết định thời điểm commit.
    """
    info = user.info
    if target is None:
        target = int((info.daily_calorie_target if info else None) or 2000)

    content, generated_by = generate_content(db, user, target, note)

    old = (
        db.query(NutritionPlan)
        .filter(NutritionPlan.user_id == user.id, NutritionPlan.status == "ACTIVE")  # type: ignore
        .order_by(NutritionPlan.version.desc())  # type: ignore
        .first()
    )
    if old:
        old.status = old_status  # type: ignore

    plan = NutritionPlan(
        user_id=user.id,
        version=(int(old.version) + 1) if old else 1,  # type: ignore
        start_date=date.today(),
        end_date=date.today() + timedelta(days=PLAN_VALID_DAYS - 1),
        daily_kcal_target=target,
        goal=info.goal if info else "MAINTAIN",
        content=content,
        generated_by=generated_by,
        status="ACTIVE",
    )
    db.add(plan)
    record_weight_snapshot(db, user)
    return plan


def plan_to_dict(plan: NutritionPlan, user: User) -> dict:
    """Hình dạng JSON trang Lộ trình (Plan.jsx) đang đọc."""
    return {
        "id": plan.id,
        "version": plan.version,
        "start_date": plan.start_date,
        "end_date": plan.end_date,
        "goal": plan.goal,
        "daily_kcal_target": plan.daily_kcal_target,
        "content": plan.content,
        "status": plan.status,
        "generated_by": plan.generated_by,
        "bmi": user.info.bmi if user.info else None,
    }

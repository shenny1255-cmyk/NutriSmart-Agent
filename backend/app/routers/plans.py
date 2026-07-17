import json
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.deps import get_db, get_current_user
from app.models import User, NutritionPlan
from app.services import ollama_client
from app.services.nutrition_context import gather_context

router = APIRouter(prefix="/plans", tags=["plans"])


@router.get("/active")
def active_plan(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    plan = (
        db.query(NutritionPlan)
        .filter(NutritionPlan.user_id == user.id, NutritionPlan.status == "ACTIVE")  # type: ignore
        .order_by(NutritionPlan.version.desc())
        .first()
    )
    if not plan:
        raise HTTPException(404, "Chưa có lộ trình nào")
    
    # Chuyển thành dict để nhét thêm BMI cho frontend dễ dùng
    res = {
        "id": plan.id,
        "version": plan.version,
        "start_date": plan.start_date,
        "end_date": plan.end_date,
        "goal": plan.goal,
        "daily_kcal_target": plan.daily_kcal_target,
        "content": plan.content,
        "bmi": user.profile.bmi if user.profile else None
    }
    return res


@router.post("/generate")
def generate_plan(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Sinh thực đơn bằng LLM dựa trên profile + bệnh nền + dị ứng."""
    profile = user.profile
    if not profile:
        raise HTTPException(400, "Chưa có hồ sơ sức khỏe")

    target = profile.daily_calorie_target or 2000

    ctx = gather_context(db, user)
    profile_data = ctx.get("profile", {})
    conditions = ", ".join(profile_data.get("conditions") or []) or "không có"
    allergens = ", ".join(profile_data.get("allergens") or []) or "không có"
    
    prompt = f"""Bạn là một chuyên gia dinh dưỡng. Hãy tạo một lộ trình ăn uống và tập luyện 7 ngày cho người dùng sau:
- Giới tính: {profile_data.get('gender')}
- Tuổi: {profile_data.get('age')}
- Chiều cao: {profile_data.get('height_cm')} cm
- Cân nặng: {profile_data.get('weight_kg')} kg
- BMI: {profile_data.get('bmi')}
- Mục tiêu: {profile_data.get('goal')}
- Lượng calo mục tiêu mỗi ngày: {target} kcal
- Bệnh nền: {conditions}
- Dị ứng: {allergens}

YÊU CẦU BẮT BUỘC:
1. ĐA DẠNG MÓN ĂN: Các món Sáng/Trưa/Tối phải cực kỳ phong phú, ưu tiên món ăn Việt Nam thực tế, đổi mới liên tục qua 7 ngày (không lặp đi lặp lại).
2. ĐA DẠNG BÀI TẬP: Đề xuất bài tập thể dục thay đổi mỗi ngày (ví dụ: chạy bộ, gym, yoga, HIIT, bơi lội...).
3. ĐỊNH DẠNG CHUẨN: Trả về KẾT QUẢ ĐẦU RA LÀ ĐÚNG MỘT CHUỖI JSON DUY NHẤT. KHÔNG kèm theo bất kỳ văn bản giải thích nào khác. Đảm bảo cấu trúc JSON như sau:
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
Lưu ý: Mảng "days" phải có đúng 7 phần tử (7 ngày). Tổng kcal mỗi ngày phải xấp xỉ {target} kcal. Tuyệt đối KHÔNG có markdown, KHÔNG có text bên ngoài JSON.
"""

    content = None
    try:
        reply = ollama_client.chat([{"role": "user", "content": prompt}], timeout=180.0)
        
        # Xử lý cắt bỏ markdown code block nếu LLM lỡ sinh ra
        reply = reply.strip()
        if reply.startswith("```json"):
            reply = reply[7:]
        if reply.startswith("```"):
            reply = reply[3:]
        if reply.endswith("```"):
            reply = reply[:-3]
        reply = reply.strip()
        
        content = json.loads(reply)
        
        if "days" not in content or not isinstance(content["days"], list):
            raise ValueError("Missing 'days' array in JSON")
            
    except Exception as e:
        print(f"Lỗi khi sinh JSON bằng AI: {e}. Trả về dữ liệu mẫu.")
        content = {
            "days": [
                {
                    "meals": [
                        {"type": "Sáng", "name": "Phở bò (Mẫu)", "kcal": int(target * 0.3)},
                        {"type": "Trưa", "name": "Cơm gà (Mẫu)", "kcal": int(target * 0.4)},
                        {"type": "Tối", "name": "Salad (Mẫu)", "kcal": int(target * 0.3)},
                    ],
                    "exercise": "Đi bộ 30 phút",
                }
                for _ in range(7)
            ]
        }

    # Hạ plan cũ xuống REVISED
    old = (
        db.query(NutritionPlan)
        .filter(NutritionPlan.user_id == user.id, NutritionPlan.status == "ACTIVE")  # type: ignore
        .order_by(NutritionPlan.version.desc())
        .first()
    )
    if old:
        old.status = "REVISED"

    plan = NutritionPlan(
        user_id=user.id,
        version=(old.version + 1) if old else 1,
        parent_plan_id=old.id if old else None,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=7),
        daily_kcal_target=target,
        goal=profile.goal,
        content=content,
        generated_by="ai-gemma3",
        status="ACTIVE",
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    
    res = {
        "id": plan.id,
        "version": plan.version,
        "start_date": plan.start_date,
        "end_date": plan.end_date,
        "goal": plan.goal,
        "daily_kcal_target": plan.daily_kcal_target,
        "content": plan.content,
        "bmi": user.profile.bmi if user.profile else None
    }
    return res
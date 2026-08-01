from sqlalchemy.orm import Session
from app.models import User, Drug


_SAFETY = (
    "Bạn là trợ lý dinh dưỡng NutriSmart Agent, tư vấn sức khỏe và dinh dưỡng cá nhân hóa. "
    "Bạn không phải bác sĩ hay chuyên gia y tế, không thay thế chẩn đoán hay điều trị y khoa. "
    "Bạn trả lời bằng tiếng Việt, lịch sự, ngắn gọn và có căn cứ khoa học."
)


def get_country_drug_rules(db: Session, country_code: str = "VN") -> tuple[str, list[dict]]:
    drugs = db.query(Drug).filter(Drug.deleted_at.is_(None)).all()

    rule_list = [
        {
            "drug_name": d.name,
            "active_ingredient": d.active_ingredient,
            "country_code": "VN",
            "country_name": "Việt Nam",
            "status": d.status,
            "note": d.status_note,
        }
        for d in drugs
    ]
    return "Việt Nam", rule_list


# Từ khóa cho thấy người dùng đang hỏi về thuốc chứ không phải dinh dưỡng
_TU_KHOA_THUOC = (
    "thuốc", "dược", "kê đơn", "liều dùng", "liều lượng", "tác dụng phụ",
    "chống chỉ định", "biệt dược", "hoạt chất", "viên uống",
)


def lien_quan_den_thuoc(message: str | None, drug_rules: list[dict]) -> bool:
    """Câu hỏi có nhắc tới thuốc (theo tên/hoạt chất trong danh mục hoặc từ khóa chung)?"""
    if not message:
        return False

    noi_dung = message.lower()

    for r in drug_rules or []:
        for ten in (r.get("drug_name"), r.get("active_ingredient")):
            if ten and ten.lower() in noi_dung:
                return True

    return any(tu in noi_dung for tu in _TU_KHOA_THUOC)


def render_drug_directive(message: str | None, drug_rules: list[dict]) -> str:
    """Khối ràng buộc quy định dược phẩm (task 9) — chuỗi rỗng nếu câu hỏi không về thuốc.

    Khối này ra lệnh ghi đè lên tài liệu RAG nên chỉ được chèn đúng lúc; gắn vào mọi
    câu hỏi sẽ khiến trợ lý từ chối trả lời các câu hỏi dinh dưỡng thuần túy.
    """
    if not lien_quan_den_thuoc(message, drug_rules):
        return ""

    return (
        "\n\n==================================================\n"
        "QUY TẮC BẮT BUỘC VỀ QUY ĐỊNH DƯỢC PHẨM (TUÂN THỦ TỰ ĐỘNG 100%):\n"
        "Khi câu hỏi liên quan tới thuốc, bạn BẮT BUỘC phải dựa vào DANH MỤC QUY ĐỊNH DƯỢC PHẨM CỦA HỆ THỐNG NUTRISMART THEO QUỐC GIA ở trên để trả lời.\n"
        "Với TRẠNG THÁI PHÁP LÝ của thuốc, BẮT BUỘC ƯU TIÊN VÀ GHI ĐÈ dữ liệu trong cơ sở dữ liệu lên trên mọi tài liệu tham khảo RAG, tri thức huấn luyện cũ, VÀ CẢ CÁC TIN NHẮN CỦA TRỢ LÝ TRONG LỊCH SỬ HỘI THOẠI:\n"
        "- Nếu tại quốc gia đó thuốc/hoạt chất có trạng thái CHO PHÉP (ALLOWED): Bạn BẮT BUỘC trả lời là thuốc ĐƯỢC PHÉP SỬ DỤNG tại quốc gia đó. TUYỆT ĐỐI KHÔNG TRẢ LỜI LÀ BỊ CẤM HAY CẤM LƯU HÀNH (dù trong lịch sử chat tin nhắn cũ từng bảo bị cấm).\n"
        "- Nếu tại quốc gia đó thuốc/hoạt chất có trạng thái HẠN CHẾ (RESTRICTED): Bạn BẮT BUỘC trả lời là thuốc bị HẠN CHẾ SỬ DỤNG (THUỐC KÊ ĐƠN) tại quốc gia đó, cần chỉ định của bác sĩ.\n"
        "- Nếu tại quốc gia đó thuốc/hoạt chất có trạng thái CẤM (BANNED): Bạn BẮT BUỘC trả lời là thuốc ĐÃ BỊ CẤM LƯU HÀNH VÀ SỬ DỤNG tại quốc gia đó.\n"
        "=================================================="
    )


def render_system_prompt(ctx: dict) -> str:
    lines = [_SAFETY, ""]

    name = ctx.get("full_name")
    if name:
        lines.append(f"Bạn đang trò chuyện với {name}.")

    profile = ctx.get("profile")
    if profile:
        conditions = ", ".join(profile.get("conditions") or []) or "không có"
        allergens = ", ".join(profile.get("allergens") or []) or "không có"
        lines.append("Hồ sơ người dùng:")
        lines.append(
            f"- Mục tiêu: {profile['goal']} · "
            f"Mục tiêu calo: {profile['daily_calorie_target']} kcal/ngày"
        )
        lines.append(
            f"- Giới tính: {profile['gender']} · Tuổi: {profile['age']} · "
            f"Cao {profile['height_cm']}cm · Nặng {profile['weight_kg']}kg · "
            f"BMI {profile['bmi']}"
        )
        lines.append(f"- Bệnh nền: {conditions} · Dị ứng: {allergens}")
    else:
        lines.append(
            "Người dùng chưa hoàn thiện hồ sơ sức khỏe. Hãy trả lời chung chung và "
            "gợi ý họ cập nhật hồ sơ để nhận tư vấn cá nhân hóa hơn."
        )

    plan = ctx.get("active_plan")
    if plan:
        lines.append(
            f"Lộ trình đang áp dụng: phiên bản {plan['version']}, "
            f"{plan['daily_kcal_target']} kcal/ngày."
        )

    tracking = ctx.get("tracking")
    if tracking:
        lines.append(
            f"Theo dõi {tracking['days']} ngày gần đây: trung bình nạp "
            f"{tracking['avg_intake']:.0f} kcal, tiêu hao {tracking['avg_burned']:.0f} "
            "kcal mỗi ngày."
        )

    user_country_code = ctx.get("country_code") or "VN"
    user_country_name = ctx.get("country_name") or "Việt Nam"
    drug_rules = ctx.get("drug_rules") or []

    lines.append("")
    lines.append(f"Quốc gia mặc định của người dùng: {user_country_name} ({user_country_code})")
    if drug_rules:
        lines.append("DANH MỤC QUY ĐỊNH DƯỢC PHẨM CỦA HỆ THỐNG NUTRISMART THEO QUỐC GIA:")
        for r in drug_rules:
            st_val = r["status"]
            c_code = r.get("country_code") or user_country_code
            c_name = r.get("country_name") or c_code

            if st_val == "BANNED":
                st = "CẤM (BANNED)"
            elif st_val == "RESTRICTED":
                st = "HẠN CHẾ SỬ DỤNG (RESTRICTED - THUỐC KÊ ĐƠN)"
            else:
                st = "CHO PHÉP (ALLOWED)"

            ing = f" ({r['active_ingredient']})" if r.get("active_ingredient") else ""
            note_str = f" - Ghi chú: {r['note']}" if r.get("note") else ""
            lines.append(f"- Thuốc/Hoạt chất {r['drug_name']}{ing} tại {c_name} ({c_code}): Trạng thái {st}{note_str}")

    return "\n".join(lines)


def gather_context(db: Session, user: User, tracking_days: int = 7) -> dict:
    country_code = getattr(user, "country_code", None) or "VN"
    country_name, drug_rules = get_country_drug_rules(db, country_code)
    full_name = user.info.full_name if user.info else "Người dùng"

    ctx: dict = {
        "full_name": full_name,
        "country_code": country_code,
        "country_name": country_name,
        "drug_rules": drug_rules,
        "profile": None,
        "active_plan": None,
        "tracking": None,
    }

    if user.profile:
        hp = user.profile
        from datetime import date
        age = (date.today() - hp.birth_date).days // 365 if hp.birth_date else None
        conditions = [c.name for c in getattr(hp, "conditions", [])]
        allergens = [a.name for a in getattr(hp, "allergens", [])]
        ctx["profile"] = {
            "goal": hp.goal,
            "gender": hp.gender,
            "age": age,
            "height_cm": hp.height_cm,
            "weight_kg": hp.weight_kg,
            "bmi": hp.bmi,
            "daily_calorie_target": hp.daily_calorie_target,
            "conditions": conditions,
            "allergens": allergens,
        }

    try:
        from app.models import NutritionPlan
        plan = (
            db.query(NutritionPlan)
            .filter(NutritionPlan.user_id == user.id)
            .order_by(NutritionPlan.version.desc())
            .first()
        )
        if plan:
            ctx["active_plan"] = {
                "version": plan.version,
                "daily_kcal_target": plan.daily_kcal_target,
            }
    except Exception:
        pass

    return ctx


def build_system_prompt(db: Session, user: User) -> str:
    ctx = gather_context(db, user)
    return render_system_prompt(ctx)

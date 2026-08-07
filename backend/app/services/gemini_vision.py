import json
import logging
import os
from google import genai
from google.genai import types
from app.config import settings

logger = logging.getLogger(__name__)

FOOD_ANALYSIS_PROMPT = """
Bạn là một chuyên gia dinh dưỡng AI. Trước tiên phải xác định ảnh có thực sự chứa món ăn hoặc đồ uống có thể phân tích dinh dưỡng hay không.

Không được đoán tên món ăn khi ảnh là người, phong cảnh, vật dụng, hình vẽ không có đồ ăn, ảnh quá mờ hoặc món ăn bị che khuất. Khi đó đặt is_food_image=false và mọi trường dinh dưỡng là null.

Yêu cầu phản hồi: BẮT BUỘC chỉ trả về duy nhất 1 chuỗi JSON hợp lệ (không kèm Markdown codeblock ```json, không kèm câu giải thích thêm).

Cấu trúc JSON bắt buộc:
{
  "is_food_image": true,
  "food_probability": 0.95,
  "rejection_reason": null,
  "food_name": "Tên món ăn bằng tiếng Việt (ví dụ: Cơm tấm sườn nướng trứng ốp la, Phở bò chín, Salad ức gà)",
  "calories_kcal": 620.0,
  "protein_g": 32.0,
  "carb_g": 70.0,
  "fat_g": 22.0,
  "description": "Mô tả ngắn về thành phần dinh dưỡng ước tính trong đĩa thức ăn",
  "confidence": 0.92
}

Nếu không phải ảnh món ăn hoặc không đủ rõ:
{
  "is_food_image": false,
  "food_probability": 0.05,
  "rejection_reason": "Lý do ngắn gọn bằng tiếng Việt",
  "food_name": null,
  "calories_kcal": null,
  "protein_g": null,
  "carb_g": null,
  "fat_g": null,
  "description": null,
  "confidence": 0.0
}
"""

MIN_FOOD_PROBABILITY = 0.70


def _rejected_analysis(reason: str, probability: float = 0.0) -> dict:
    return {
        "is_food_image": False,
        "food_probability": max(0.0, min(1.0, probability)),
        "rejection_reason": reason,
        "food_name": None,
        "calories_kcal": None,
        "protein_g": None,
        "carb_g": None,
        "fat_g": None,
        "description": None,
        "confidence": 0.0,
    }


def normalize_food_analysis(parsed: dict) -> dict:
    """Chuẩn hóa phản hồi AI và từ chối an toàn thay vì tự bịa dữ liệu món ăn."""
    if parsed.get("is_food_image") is not True:
        probability = float(parsed.get("food_probability") or 0.0)
        reason = parsed.get("rejection_reason") or "AI không xác nhận đây là ảnh món ăn."
        return _rejected_analysis(str(reason), probability)

    probability = float(parsed.get("food_probability") or 0.0)
    if probability < MIN_FOOD_PROBABILITY:
        return _rejected_analysis(
            "Không đủ chắc chắn đây là ảnh món ăn rõ ràng. Vui lòng chọn ảnh khác.",
            probability,
        )

    required = ("food_name", "calories_kcal", "protein_g", "carb_g", "fat_g")
    if any(parsed.get(field) is None for field in required):
        raise ValueError("Phản hồi AI thiếu dữ liệu dinh dưỡng bắt buộc")

    return {
        "is_food_image": True,
        "food_probability": min(1.0, probability),
        "rejection_reason": None,
        "food_name": str(parsed["food_name"]).strip(),
        "calories_kcal": float(parsed["calories_kcal"]),
        "protein_g": float(parsed["protein_g"]),
        "carb_g": float(parsed["carb_g"]),
        "fat_g": float(parsed["fat_g"]),
        "description": str(parsed.get("description") or "Ước tính dinh dưỡng từ ảnh món ăn."),
        "confidence": max(0.0, min(1.0, float(parsed.get("confidence") or probability))),
    }

def analyze_food_image(image_bytes: bytes, mime_type: str = "image/jpeg") -> dict:
    """
    Sử dụng Gemini Flash AI phân tích ảnh món ăn và trả về dict dinh dưỡng.
    """
    api_key = settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError("GEMINI_API_KEY chưa được cấu hình")

    client = genai.Client(api_key=api_key)

    # Ưu tiên gemini-flash-latest (model khả dụng nhất trên Google AI Studio)
    candidate_models = ['gemini-flash-latest', 'gemini-2.5-flash', 'gemini-2.0-flash-lite', 'gemini-2.0-flash']
    last_exception = None

    for model_name in candidate_models:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=[
                    types.Part.from_bytes(
                        data=image_bytes,
                        mime_type=mime_type,
                    ),
                    FOOD_ANALYSIS_PROMPT
                ],
                config=types.GenerateContentConfig(  # type: ignore
                    temperature=0.2,  # type: ignore
                    response_mime_type="application/json",  # type: ignore
                ),
            )

            raw_text = response.text or ""
            text_content = raw_text.strip()
            if text_content.startswith("```json"):
                text_content = text_content[7:]
            if text_content.startswith("```"):
                text_content = text_content[3:]
            if text_content.endswith("```"):
                text_content = text_content[:-3]
            text_content = text_content.strip()

            parsed = json.loads(text_content)
            logger.info(f"Phân tích thành công bằng Gemini model: {model_name}")
            return normalize_food_analysis(parsed)
        except Exception as e:
            logger.warning(f"Thử model {model_name} không thành công: {e}")
            last_exception = e
            continue

    logger.error(f"Tất cả các model Gemini đều thất bại: {last_exception}", exc_info=True)
    raise RuntimeError("Gemini Vision tạm thời không phản hồi") from last_exception

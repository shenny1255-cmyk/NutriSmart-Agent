"""Chặn câu hỏi ngoài phạm vi dinh dưỡng - sức khỏe TRƯỚC khi gọi LLM.

Chỉ dặn trong system prompt là không đủ: gemma3:1b vẫn hướng dẫn "thay lốp xe máy" dù prompt đã cấm
(QA nghiệm thu, ca 3.3e). Bộ chặn này không phụ thuộc model và thiên về CHO QUA: chỉ từ chối khi
đồng thời
  1. kho tài liệu không có đoạn nào liên quan (RAG rỗng),
  2. câu hỏi không chứa từ nào thuộc lĩnh vực ăn uống, vận động, sức khỏe hay ứng dụng,
  3. không phải câu hỏi nối tiếp ngắn trong một cuộc trò chuyện đang diễn ra ("còn buổi tối thì sao?").
Kiểm trên bộ 59 câu GĐ2: không từ chối nhầm câu đúng chủ đề nào (xem tests/test_topic_guard.py).
"""
from __future__ import annotations

import re
import unicodedata

from app.services.accent_restore import has_diacritics, strip_accents

REFUSAL = (
    "Câu hỏi này nằm ngoài phạm vi hỗ trợ của NutriSmart. Mình chỉ tư vấn về dinh dưỡng, ăn uống, "
    "vận động và sức khỏe. Bạn có thể hỏi, ví dụ: \"Bữa tối nay mình nên ăn gì để đủ đạm mà không vượt calo?\""
)

FOLLOW_UP_MAX_WORDS = 6

_DOMAIN = (
    # ăn uống
    "ăn", "uống", "món", "bữa", "thực đơn", "thực phẩm", "đồ ăn", "nấu", "khẩu phần", "kiêng",
    "calo", "kcal", "năng lượng", "dinh dưỡng", "đạm", "protein", "tinh bột", "carb", "chất béo",
    # "nước" đứng một mình mang cả nghĩa "quốc gia" → chỉ nhận cụm rõ nghĩa đồ uống
    "chất xơ", "vitamin", "khoáng", "canxi", "sắt", "muối", "đường", "nước lọc", "nước ép",
    "nước ngọt", "nước mắm", "nước dừa", "nước cam", "mất nước", "uống nước", "rau", "quả", "cơ thể",
    "trái cây", "thịt", "cá", "trứng", "sữa", "gạo", "cơm", "phở", "bún", "bánh", "chè", "bia", "rượu",
    "cà phê", "trà", "hạt", "đậu", "purin", "gi", "chỉ số đường huyết",
    # cơ thể, vận động
    "giảm cân", "tăng cân", "cân nặng", "béo phì", "thừa cân", "gầy", "bmi", "vòng eo", "tăng cơ",
    "cơ bắp", "tập", "tập luyện", "thể dục", "vận động", "chạy bộ", "đi bộ", "gym", "yoga", "bơi",
    "số bước", "ngủ", "giấc ngủ", "stress",
    # sức khỏe
    "sức khỏe", "bệnh", "tiểu đường", "đái tháo đường", "huyết áp", "gout", "gút", "mỡ máu",
    "cholesterol", "lipid", "thận", "gan", "dạ dày", "trào ngược", "tim mạch", "dị ứng", "thuốc",
    "bác sĩ", "triệu chứng", "mang thai", "bà bầu", "cho con bú", "acid uric", "insulin",
    # ứng dụng, chào hỏi
    "nutrismart", "lộ trình", "nhật ký", "check-in", "hồ sơ", "mục tiêu", "xin chào", "chào",
    "cảm ơn", "cám ơn", "bạn là ai", "giúp gì",
)


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", s or "").lower()).strip()


def _contains(text: str, phrase: str) -> bool:
    return re.search(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", text) is not None


def has_domain_term(message: str) -> bool:
    """Câu có dấu so khớp nguyên dấu; câu không dấu so khớp bản bỏ dấu của từ điển.

    Không bỏ dấu câu có dấu: "có" bỏ dấu thành "co" sẽ trùng "cơ", câu nào cũng lọt.
    """
    text = _norm(message)
    if has_diacritics(text):
        return any(_contains(text, p) for p in _DOMAIN)
    return any(_contains(text, strip_accents(p)) for p in _DOMAIN)


def is_in_scope(message: str, *, has_rag_hits: bool, in_conversation: bool) -> bool:
    if has_rag_hits or has_domain_term(message):
        return True
    return in_conversation and len(_norm(message).split()) <= FOLLOW_UP_MAX_WORDS

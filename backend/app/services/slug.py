"""Sinh slug từ tên tiếng Việt cho danh mục tài liệu."""
import re
import unicodedata

SLUG_THAY_THE = "danh-muc"   # dùng khi tên chỉ toàn ký tự đặc biệt


def tao_slug(ten: str) -> str:
    """'Đái tháo đường' -> 'dai-thao-duong'.

    unicodedata không tách được chữ đ/Đ (nó là ký tự riêng chứ không phải d + dấu),
    nên phải thay tay trước khi chuẩn hóa.
    """
    chuoi = (ten or "").strip().lower().replace("đ", "d")
    chuoi = unicodedata.normalize("NFD", chuoi)
    chuoi = "".join(c for c in chuoi if unicodedata.category(c) != "Mn")
    chuoi = re.sub(r"[^a-z0-9]+", "-", chuoi).strip("-")
    return chuoi or SLUG_THAY_THE

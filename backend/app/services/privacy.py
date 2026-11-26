"""Ẩn danh hóa dữ liệu trước khi gửi ra nhà cung cấp AI bên ngoài (kế hoạch ĐATN v2, mục 3).

Theo Nghị định 13/2023/NĐ-CP, dữ liệu sức khỏe là dữ liệu cá nhân nhạy cảm. Nguyên tắc
tối thiểu hóa: chỉ gửi những gì cần cho tư vấn dinh dưỡng.

- Xóa: họ tên người dùng, email, số điện thoại.
- Làm mờ: tuổi chính xác → khoảng tuổi (cả "Tuổi: N" trong hồ sơ lẫn "N tuổi" người dùng tự gõ).
- Giữ: giới tính, chiều cao, cân nặng, bệnh nền, dị ứng, mục tiêu calo (cần để tư vấn).

Chỉ áp dụng khi gọi AI cloud; Ollama chạy nội bộ thì dữ liệu không rời máy chủ.
"""
from __future__ import annotations

import re

NAME_PLACEHOLDER = "người dùng"

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
# Số điện thoại VN: 0xxx hoặc +84xxx, 9-10 chữ số sau đầu số, cho phép khoảng trắng/chấm/gạch.
_PHONE = re.compile(r"(?<!\w)(?:\+84|0)(?:[\s.-]?\d){9,10}(?!\d)")
_AGE = re.compile(r"(Tuổi:\s*)(\d{1,3})")
# Tuổi người dùng tự gõ trong câu: "tôi 22 tuổi", "năm nay 35 tuổi"
_AGE_FREE = re.compile(r"(?<![\w.,-])(\d{1,3})(\s*tuổi)(?!\w)", re.IGNORECASE)
_GREETING = re.compile(r"Bạn đang trò chuyện với [^.\n]*\.?")


def age_band(age: int) -> str:
    if age < 18:
        return "dưới 18"
    for lo, hi in ((18, 24), (25, 34), (35, 44), (45, 54), (55, 64)):
        if lo <= age <= hi:
            return f"{lo}-{hi}"
    return "65+"


def _anonymize_text(text: str, full_name: str | None, report: dict) -> str:
    text, n = _GREETING.subn(f"Bạn đang trò chuyện với {NAME_PLACEHOLDER}.", text)
    report["name"] += n
    if full_name and full_name.strip():
        pattern = re.compile(re.escape(full_name.strip()), re.IGNORECASE)
        text, n = pattern.subn(NAME_PLACEHOLDER, text)
        report["name"] += n
    text, n = _EMAIL.subn("[email]", text)
    report["email"] += n
    text, n = _PHONE.subn("[số điện thoại]", text)
    report["phone"] += n

    def _band(m: re.Match) -> str:
        report["age"] += 1
        return m.group(1) + age_band(int(m.group(2)))

    def _band_free(m: re.Match) -> str:
        report["age"] += 1
        return age_band(int(m.group(1))) + m.group(2)
    text = _AGE.sub(_band, text)
    return _AGE_FREE.sub(_band_free, text)


def anonymize_messages(messages: list[dict], *, full_name: str | None = None,
                       email: str | None = None) -> tuple[list[dict], dict]:
    """Trả về (bản sao messages đã ẩn danh, số lượng mục bị xóa theo loại).

    `email` của tài khoản đã được regex email bao phủ; tham số giữ để caller truyền đủ ngữ cảnh.
    """
    report = {"name": 0, "email": 0, "phone": 0, "age": 0}
    out = [{**m, "content": _anonymize_text(str(m.get("content") or ""), full_name, report)}
           for m in messages]
    return out, report

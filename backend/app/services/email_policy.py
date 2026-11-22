"""Chính sách email khi ĐĂNG KÝ: chỉ nhận nhà cung cấp chính thống, chống tài khoản rác."""
from __future__ import annotations

from app.config import settings

ALLOWED_DOMAINS = frozenset({
    "gmail.com", "googlemail.com",
    "outlook.com", "outlook.com.vn", "hotmail.com", "live.com", "msn.com",
    "yahoo.com", "yahoo.com.vn", "ymail.com",
    "icloud.com", "me.com", "mac.com",
    "proton.me", "protonmail.com", "zoho.com",
})
ALLOWED_SUFFIXES = (".edu.vn", ".gov.vn")   # email trường học, cơ quan
GMAIL_DOMAINS = frozenset({"gmail.com", "googlemail.com"})

MSG_DOMAIN = ("Chỉ chấp nhận email từ nhà cung cấp chính thống (Gmail, Outlook, Yahoo, iCloud...) "
              "hoặc email trường học/cơ quan (.edu.vn, .gov.vn).")
MSG_ALIAS = "Không dùng địa chỉ có dấu '+' (bí danh). Hãy nhập email gốc của bạn."


def _split(email: str) -> tuple[str, str]:
    local, _, domain = email.strip().lower().rpartition("@")
    return local, domain


def _extra_domains() -> set[str]:
    raw = getattr(settings, "ALLOWED_EMAIL_DOMAINS", "") or ""
    return {d.strip().lower().lstrip("@") for d in raw.split(",") if d.strip()}


def is_domain_allowed(domain: str) -> bool:
    if domain in ALLOWED_DOMAINS or domain in _extra_domains():
        return True
    return any(domain.endswith(s) for s in ALLOWED_SUFFIXES)


def rejection_reason(email: str) -> str | None:
    """Trả lý do từ chối, hoặc None nếu được phép đăng ký."""
    local, domain = _split(email)
    if not local or not is_domain_allowed(domain):
        return MSG_DOMAIN
    if "+" in local:
        return MSG_ALIAS
    return None


def is_gmail(email: str) -> bool:
    return _split(email)[1] in GMAIL_DOMAINS


def canonical(email: str) -> str:
    """Gmail bỏ qua dấu chấm và +tag: n.guyen+1@gmail.com = nguyen@gmail.com."""
    local, domain = _split(email)
    if domain in GMAIL_DOMAINS:
        local = local.split("+", 1)[0].replace(".", "")
        domain = "gmail.com"
    return f"{local}@{domain}"
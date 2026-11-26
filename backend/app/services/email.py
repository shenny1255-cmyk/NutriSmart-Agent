"""Gửi email xác minh.

- Có SMTP_HOST → gửi thật qua smtplib (STARTTLS).
- Không cấu hình SMTP → ghi link ra log (dev/offline vẫn hoạt động).
- Lỗi gửi mail KHÔNG bao giờ raise ra luồng request - chỉ fallback ghi log.
"""

import logging
import smtplib
from email.message import EmailMessage

from app.config import settings

log = logging.getLogger("nutrismart.email")
# Đảm bảo log (nhất là link xác minh ở chế độ console) luôn hiện, kể cả khi
# logging toàn cục mặc định ở mức WARNING.
if not log.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(levelname)s:%(name)s:%(message)s"))
    log.addHandler(_handler)
    log.setLevel(logging.INFO)
    log.propagate = False


def build_verify_link(token: str) -> str:
    return f"{settings.APP_BASE_URL.rstrip('/')}/verify?token={token}"


def _body(verify_link: str) -> str:
    return (
        "Chào bạn,\n\n"
        "Nhấp vào liên kết sau để xác minh email của bạn cho tài khoản NutriSmart:\n"
        f"{verify_link}\n\n"
        "Liên kết có hiệu lực trong 24 giờ. Nếu bạn không đăng ký, hãy bỏ qua email này.\n\n"
        "- NutriSmart"
    )


def send_verification_email(to_email: str, verify_link: str) -> None:
    if not settings.SMTP_HOST:
        log.info("[email:console] gửi tới %s - link xác minh: %s", to_email, verify_link)
        return

    msg = EmailMessage()
    msg["Subject"] = "Xác minh email NutriSmart"
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to_email
    msg.set_content(_body(verify_link))

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as s:
            s.starttls()
            if settings.SMTP_USER:
                s.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            s.send_message(msg)
        log.info("[email:smtp] đã gửi email xác minh tới %s", to_email)
    except Exception as e:  # noqa: BLE001 - không để lỗi mail làm hỏng đăng ký
        log.warning("[email:smtp] gửi thất bại (%s) - link cho %s: %s", e, to_email, verify_link)


def send_pin_email(to_email: str, pin: str) -> None:
    """Gửi mã PIN 6 chữ số để xác thực email khi đăng ký tài khoản mới."""
    if not settings.SMTP_HOST:
        log.info("[email:console] gửi mã PIN tới %s - MÃ PIN: %s", to_email, pin)
        return

    msg = EmailMessage()
    msg["Subject"] = f"Mã xác nhận đăng ký NutriSmart: {pin}"
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to_email
    msg.set_content(
        "Chào bạn,\n\n"
        f"Mã PIN xác nhận đăng ký tài khoản NutriSmart của bạn là: {pin}\n\n"
        "Mã có hiệu lực trong 10 phút. Tuyệt đối không chia sẻ mã này với bất kỳ ai.\n"
        "Nếu bạn không yêu cầu đăng ký, vui lòng bỏ qua email này.\n\n"
        "- NutriSmart"
    )

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as s:
            s.starttls()
            if settings.SMTP_USER:
                s.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            s.send_message(msg)
        log.info("[email:smtp] đã gửi mã PIN tới %s", to_email)
    except Exception as e:  # noqa: BLE001 - không làm treo API nếu SMTP lỗi
        log.warning("[email:smtp] gửi mã PIN thất bại (%s) - PIN cho %s: %s", e, to_email, pin)

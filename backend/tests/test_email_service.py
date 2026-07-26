"""services/email: gửi SMTP khi có cấu hình, ngược lại ghi link ra log; lỗi SMTP không được raise."""

import logging

import app.services.email as email_mod
from app.services.email import build_verify_link, send_verification_email
from app.config import settings

LINK = "http://localhost:5173/verify?token=TESTTOKEN"


def test_build_verify_link():
    link = build_verify_link("abc123")
    assert link == settings.APP_BASE_URL.rstrip("/") + "/verify?token=abc123"


def test_console_fallback_logs_link_when_smtp_unset(monkeypatch, caplog):
    monkeypatch.setattr(settings, "SMTP_HOST", "")
    with caplog.at_level(logging.INFO, logger="nutrismart.email"):
        send_verification_email("user@example.com", LINK)   # không được raise
    assert any(LINK in r.getMessage() for r in caplog.records)


def test_smtp_path_sends_message_with_link(monkeypatch):
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr(settings, "SMTP_USER", "u@example.com")
    monkeypatch.setattr(settings, "SMTP_PASSWORD", "app-pw")
    captured = {}

    class FakeSMTP:
        def __init__(self, host, port, timeout=None):
            captured["host"] = host
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False
        def starttls(self):
            captured["tls"] = True
        def login(self, u, p):
            captured["login"] = (u, p)
        def send_message(self, msg):
            captured["body"] = msg.get_content()

    monkeypatch.setattr(email_mod.smtplib, "SMTP", FakeSMTP)
    send_verification_email("to@example.com", LINK)

    assert captured["host"] == "smtp.example.com"
    assert captured["tls"] is True
    assert captured["login"] == ("u@example.com", "app-pw")
    assert LINK in captured["body"]


def test_smtp_failure_falls_back_and_does_not_raise(monkeypatch, caplog):
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.example.com")

    def boom(*a, **k):
        raise OSError("connection refused")

    monkeypatch.setattr(email_mod.smtplib, "SMTP", boom)
    with caplog.at_level(logging.WARNING, logger="nutrismart.email"):
        send_verification_email("to@example.com", LINK)   # phải nuốt lỗi
    assert any(LINK in r.getMessage() for r in caplog.records)

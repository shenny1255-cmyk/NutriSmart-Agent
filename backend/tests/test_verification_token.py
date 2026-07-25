"""Token xác minh email: JWT có purpose riêng, hết hạn/sai purpose đều bị từ chối."""

from datetime import datetime, timedelta, timezone

from jose import jwt

from app.config import settings
from app.security import (
    create_verification_token,
    decode_verification_token,
    create_access_token,
)


def test_roundtrip_returns_user_id():
    tok = create_verification_token("user-123")
    assert decode_verification_token(tok) == "user-123"


def test_access_token_not_accepted_as_verification():
    # access token không có purpose="verify_email" → phải bị từ chối
    access = create_access_token("user-123")
    assert decode_verification_token(access) is None


def test_expired_verification_token_rejected():
    payload = {
        "sub": "user-123",
        "purpose": "verify_email",
        "exp": datetime.now(timezone.utc) - timedelta(hours=1),
    }
    tok = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    assert decode_verification_token(tok) is None


def test_garbage_token_rejected():
    assert decode_verification_token("not.a.valid.jwt") is None

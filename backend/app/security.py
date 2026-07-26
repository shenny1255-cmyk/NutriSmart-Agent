from datetime import datetime, timedelta, timezone

import bcrypt
from jose import jwt, JWTError

from app.config import settings


def hash_password(raw: str) -> str:
    raw_bytes = raw.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed_bytes = bcrypt.hashpw(raw_bytes, salt)
    return hashed_bytes.decode("utf-8")


def verify_password(raw: str, hashed: str) -> bool:
    raw_bytes = raw.encode("utf-8")
    hashed_bytes = hashed.encode("utf-8")
    try:
        return bcrypt.checkpw(raw_bytes, hashed_bytes)
    except Exception:
        return False


def create_access_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> str | None:
    """Trả về user_id, hoặc None nếu token sai/hết hạn."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None


def create_verification_token(user_id: str) -> str:
    """Token dùng MỘT lần để xác minh email (sống 24h), tách biệt access token bằng purpose."""
    expire = datetime.now(timezone.utc) + timedelta(hours=24)
    payload = {"sub": str(user_id), "purpose": "verify_email", "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_verification_token(token: str) -> str | None:
    """Trả về user_id nếu token hợp lệ, chưa hết hạn và đúng purpose; ngược lại None."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        return None
    if payload.get("purpose") != "verify_email":
        return None
    return payload.get("sub")
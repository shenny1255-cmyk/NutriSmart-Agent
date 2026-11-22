from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import User
from app.security import decode_token

bearer = HTTPBearer(auto_error=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    cred: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if cred is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Thiếu token")

    payload = decode_token(cred.credentials)
    if payload is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token không hợp lệ")

    import uuid
    try:
        user_id = uuid.UUID(str(payload["sub"]))
    except ValueError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token không hợp lệ")
    user = db.query(User).filter(User.id == user_id).first()  # type: ignore
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Người dùng không tồn tại")

    # Đăng nhập đơn thiết bị: lần đăng nhập mới tăng token_version nên token cũ lệch "tv".
    # Miễn trừ cho các tài khoản demo để phục vụ trình diễn và chấm điểm đồ án nhiều người cùng lúc.
    demo_emails = {"demo@nutrismart.vn", "user1@nutrismart.vn", "user2@nutrismart.vn", "expert1@nutrismart.vn"}
    if str(user.email).lower() not in demo_emails and payload.get("tv") != user.token_version:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Phiên đăng nhập đã hết hạn hoặc tài khoản đã được đăng nhập trên thiết bị khác",
        )

    return user
def require_role(*allowed_roles: str):
    """Trả về dependency chặn nếu role người dùng không nằm trong allowed_roles."""
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed_roles:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                f"Yêu cầu quyền: {', '.join(allowed_roles)}",
            )
        return user
    return checker
"""Ghi nhận đồng ý xử lý dữ liệu cá nhân (Nghị định 13/2023/NĐ-CP) - kế hoạch ĐATN v2, GĐ1.

Ba mục đích tách riêng, người dùng tự tick (không tick sẵn):
- TERMS:       Điều khoản sử dụng + Chính sách quyền riêng tư (bắt buộc).
- HEALTH_DATA: xử lý dữ liệu sức khỏe (dữ liệu nhạy cảm) để tính calo, gợi ý thực đơn, cảnh báo
               an toàn (bắt buộc - thiếu thì ứng dụng không hoạt động được).
- CLOUD_AI:    gửi dữ liệu ĐÃ ẨN DANH tới AI đám mây (Google Gemini) (tùy chọn; từ chối =
               user_profile.ai_local_only = TRUE).

Bảng user_consents chỉ thêm dòng; dòng mới nhất của mỗi loại là trạng thái hiện tại.
Nội dung chính sách tương ứng phiên bản: frontend/src/pages/Privacy.jsx (POLICY_VERSION).
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import UserConsent

# Đổi nội dung chính sách → tăng phiên bản (và đồng bộ POLICY_VERSION ở Privacy.jsx).
CONSENT_VERSION = "1.1"
TYPES = ("TERMS", "HEALTH_DATA", "CLOUD_AI")


def record(db: Session, user_id, consent_type: str, granted: bool, source: str) -> None:
    """Thêm một dòng đồng ý/rút lại. Không commit - để giao dịch của nơi gọi quyết định."""
    if consent_type not in TYPES:
        raise ValueError(f"Loại đồng ý không hợp lệ: {consent_type}")
    db.add(UserConsent(user_id=user_id, consent_type=consent_type, granted=bool(granted),
                       version=CONSENT_VERSION, source=source))


def history(db: Session, user_id) -> list[UserConsent]:
    return (db.query(UserConsent).filter(UserConsent.user_id == user_id)  # type: ignore
            .order_by(UserConsent.created_at.desc(), UserConsent.id.desc()).all())

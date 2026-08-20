from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import date
from typing import Any, cast

from sqlalchemy import func, text, String
from sqlalchemy.orm import Session

from app.deps import get_db, require_role
from app.models import (
    User, UserProfile, AuditLog, DocCategory, Document,
)
from app.schemas import (
    AdminUserOut, AdminCreateUserIn, UpdateRoleIn, BulkDeleteUsersIn, BulkDeleteUsersOut,
    AuditOut, AuditListOut,
    CategoryIn, DocCategoryOut,
)
from app.services.audit import write_audit
from app.services.slug import tao_slug
from app.security import hash_password

router = APIRouter(prefix="/admin", tags=["admin"])

# Toàn bộ router này chỉ ADMIN vào được
admin_only = Depends(require_role("ADMIN"))
# Riêng danh mục tài liệu thì Chuyên gia cũng cần đọc để gắn khi tải tài liệu lên
expert_or_admin = Depends(require_role("EXPERT", "ADMIN"))




# ---------- Quản lý người dùng ----------
# Có extension unaccent thì tìm được kiểu gõ không dấu ("nguyen van" → "Nguyễn Văn An").
# Kiểm tra một lần cho mỗi tiến trình; DB nào chưa cài thì tự lùi về ilike thường.
_co_unaccent: bool | None = None


def _kiem_tra_unaccent(db: Session) -> bool:
    global _co_unaccent
    if _co_unaccent is None:
        _co_unaccent = db.execute(
            text("SELECT 1 FROM pg_extension WHERE extname = 'unaccent'")
        ).first() is not None
    return _co_unaccent


def search_users(db: Session, q: str | None) -> list[User]:
    """Danh sách user, lọc theo HỌ TÊN hoặc email khi có từ khóa."""
    query = db.query(User).outerjoin(UserProfile, UserProfile.user_id == User.id)

    tu_khoa = (q or "").strip()
    if tu_khoa:
        kw = f"%{tu_khoa}%"
        if _kiem_tra_unaccent(db):
            dieu_kien = text(
                "unaccent(coalesce(user_profile.full_name, '')) ILIKE unaccent(:kw)"
                " OR unaccent(users.email) ILIKE unaccent(:kw)"
            ).bindparams(kw=kw)
        else:
            dieu_kien = text(
                "coalesce(user_profile.full_name, '') ILIKE :kw OR users.email ILIKE :kw"
            ).bindparams(kw=kw)
        query = query.filter(dieu_kien)

    return query.order_by(User.updated_at.desc()).all()


def ensure_role_change_allowed(actor_id, target_id, new_role: str) -> None:
    """Không cho admin đang đăng nhập tự hạ quyền và tự khóa trang quản trị."""
    if actor_id == target_id and new_role != "ADMIN":
        raise HTTPException(400, "Không thể tự thay đổi vai trò ADMIN của mình")


@router.get("/users", response_model=list[AdminUserOut])
def list_users(
    q: str | None = Query(None, description="tìm theo họ tên hoặc email"),
    db: Session = Depends(get_db),
    _: User = admin_only,
):
    return search_users(db, q)


@router.post("/users", response_model=AdminUserOut, status_code=201)
def create_user(
    payload: AdminCreateUserIn,
    db: Session = Depends(get_db),
    actor: User = admin_only,
):
    if db.query(User).filter(func.lower(User.email) == str(payload.email).lower()).first():  # type: ignore
        raise HTTPException(409, "Email đã được sử dụng")

    from app.models import StaffProfile
    import uuid

    user = User(
        email=str(payload.email),
        password_hash=hash_password(payload.password),
        role=payload.role,
    )
    user.profile = UserProfile(full_name=payload.full_name)
    if payload.role in ("EXPERT", "ADMIN"):
        user.staff_profile = StaffProfile(
            staff_code=f"STF-{uuid.uuid4().hex[:6].upper()}",
            full_name=payload.full_name,
            employment_status="ACTIVE",
        )
    db.add(user)
    db.flush()
    write_audit(
        db, actor.id, "CREATE", "users", str(user.id),
        after={"email": str(payload.email), "role": payload.role},
    )
    db.commit()
    db.refresh(user)
    return user


@router.patch("/users/{user_id}/role", response_model=AdminUserOut)
def update_role(
    user_id: str, payload: UpdateRoleIn,
    db: Session = Depends(get_db),
    actor: User = admin_only,
):
    user = db.query(User).filter(User.id == user_id).first()  # type: ignore
    if not user:
        raise HTTPException(404, "Không tìm thấy người dùng")
    ensure_role_change_allowed(actor.id, user.id, payload.role)

    before = {"role": user.role}
    user.role = payload.role  # type: ignore

    # Tự đồng bộ hồ sơ nhân viên; quyền được lấy chung theo role.
    from app.models import StaffProfile
    import uuid
    if payload.role in ("EXPERT", "ADMIN"):
        if not user.staff_profile:
            staff_code = f"STF-{uuid.uuid4().hex[:6].upper()}"
            full_name = user.full_name or "Nhân viên"
            sp = StaffProfile(
                user_id=user.id,
                staff_code=staff_code,
                full_name=full_name,
                employment_status="ACTIVE",
            )
            user.staff_profile = sp
    elif payload.role == "USER" and user.staff_profile:
        db.delete(user.staff_profile)

    write_audit(db, actor.id, "UPDATE", "users", user_id,
                before=before, after={"role": payload.role})  # type: ignore
    db.commit()
    db.refresh(user)
    return user


@router.delete("/users/bulk-delete", response_model=BulkDeleteUsersOut)
def bulk_delete_users(
    payload: BulkDeleteUsersIn,
    db: Session = Depends(get_db),
    actor: User = admin_only,
):
    if actor.id in payload.user_ids:
        raise HTTPException(400, "Không thể tự xóa tài khoản của mình")

    users = db.query(User).filter(User.id.in_(payload.user_ids)).all()  # type: ignore
    for user in users:
        write_audit(db, actor.id, "DELETE", "users", str(user.id), before={
            "email": user.email, "full_name": user.full_name, "role": user.role,
        })
        db.delete(user)
    db.commit()
    return BulkDeleteUsersOut(deleted_count=len(users))


@router.delete("/users/{user_id}", status_code=204)
def soft_delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    actor: User = admin_only,
):
    from datetime import datetime, timezone
    user = db.query(User).filter(User.id == user_id).first()  # type: ignore
    if not user:
        raise HTTPException(404, "Không tìm thấy người dùng")
    if user.id == actor.id:
        raise HTTPException(400, "Không thể tự xóa tài khoản của mình")

    db.delete(user)
    write_audit(db, actor.id, "DELETE", "users", user_id, before={
        "email": user.email, "full_name": user.full_name, "role": user.role,
    })
    db.commit()


# ---------- Danh mục tài liệu ----------
# Các hàm nhận (db, actor) trực tiếp để test gọi được mà không cần dựng HTTP.

def _slug_chua_dung(db: Session, goc: str) -> str:
    """Thêm hậu tố -2, -3… nếu slug đã có (cột slug là UNIQUE)."""
    slug, i = goc, 1
    while db.query(DocCategory).filter(DocCategory.slug == slug).first():  # type: ignore
        i += 1
        slug = f"{goc}-{i}"
    return slug


def danh_sach_doc_category(db: Session) -> list[DocCategoryOut]:
    rows = (
        db.query(DocCategory, func.count(Document.id))  # type: ignore
        .outerjoin(Document, Document.category_id == DocCategory.id)  # type: ignore
        .group_by(DocCategory.id)  # type: ignore
        .order_by(DocCategory.name)  # type: ignore
        .all()
    )
    return [
        DocCategoryOut(id=int(c.id), name=str(c.name), slug=str(c.slug), parent_id=c.parent_id, so_tai_lieu=n)  # type: ignore
        for c, n in rows
    ]


def them_doc_category(db: Session, actor: User, payload: CategoryIn) -> DocCategoryOut:
    cat = DocCategory(
        name=payload.name.strip(),
        slug=_slug_chua_dung(db, tao_slug(payload.name)),
        parent_id=payload.parent_id,
    )
    db.add(cat)
    db.flush()
    write_audit(db, actor.id, "CREATE", "doc_categories", str(cat.id),
                after={"name": cat.name, "slug": cat.slug})
    db.commit()
    db.refresh(cat)
    return DocCategoryOut(id=int(cat.id), name=str(cat.name), slug=str(cat.slug), parent_id=cat.parent_id)  # type: ignore


def sua_doc_category(db: Session, actor: User, cat_id: int, payload: CategoryIn) -> DocCategoryOut:
    cat = db.query(DocCategory).filter(DocCategory.id == cat_id).first()  # type: ignore
    if not cat:
        raise HTTPException(404, "Không tìm thấy danh mục tài liệu")
    if payload.parent_id == cat_id:
        raise HTTPException(400, "Danh mục không thể là cha của chính nó")

    truoc = {"name": cat.name, "parent_id": cat.parent_id}
    cat.name = payload.name.strip()  # type: ignore
    cat.parent_id = payload.parent_id  # type: ignore
    write_audit(db, actor.id, "UPDATE", "doc_categories", str(cat_id),
                before=truoc, after={"name": cat.name, "parent_id": cat.parent_id})
    db.commit()
    db.refresh(cat)
    return DocCategoryOut(id=int(cat.id), name=str(cat.name), slug=str(cat.slug), parent_id=cat.parent_id)  # type: ignore


def xoa_doc_category(db: Session, actor: User, cat_id: int) -> None:
    """Xóa danh mục. Tài liệu thuộc danh mục KHÔNG bị xóa theo — FK là ON DELETE SET NULL."""
    cat = db.query(DocCategory).filter(DocCategory.id == cat_id).first()  # type: ignore
    if not cat:
        raise HTTPException(404, "Không tìm thấy danh mục tài liệu")

    write_audit(db, actor.id, "DELETE", "doc_categories", str(cat_id),
                before={"name": cat.name, "slug": cat.slug})
    db.delete(cat)
    db.commit()


@router.get("/doc-categories", response_model=list[DocCategoryOut])
def api_doc_categories(db: Session = Depends(get_db), _: User = expert_or_admin):
    return danh_sach_doc_category(db)


@router.post("/doc-categories", response_model=DocCategoryOut, status_code=201)
def api_them_doc_category(payload: CategoryIn, db: Session = Depends(get_db), actor: User = admin_only):
    return them_doc_category(db, actor, payload)


@router.patch("/doc-categories/{cat_id}", response_model=DocCategoryOut)
def api_sua_doc_category(cat_id: int, payload: CategoryIn,
                         db: Session = Depends(get_db), actor: User = admin_only):
    return sua_doc_category(db, actor, cat_id, payload)


@router.delete("/doc-categories/{cat_id}", status_code=204)
def api_xoa_doc_category(cat_id: int, db: Session = Depends(get_db), actor: User = admin_only):
    xoa_doc_category(db, actor, cat_id)


# ---------- Audit logs ----------
def _safe_audit_data(data: dict | None) -> dict | None:
    if not data:
        return None
    blocked = ("password", "token", "secret", "hash")
    return {key: value for key, value in data.items() if not any(word in key.lower() for word in blocked)}


def _audit_description(action: str, entity: str, target: str) -> str:
    action_label = {"CREATE": "đã tạo", "UPDATE": "đã cập nhật", "DELETE": "đã xóa", "APPROVE": "đã phê duyệt"}.get(action, action.lower())
    entity_label = {"users": "tài khoản", "doc_categories": "danh mục", "documents": "tài liệu", "chat_messages": "tin nhắn"}.get(entity, entity)
    return f"{action_label.capitalize()} {entity_label} {target}".strip()


def validate_audit_date_range(date_from: date | None, date_to: date | None) -> None:
    today = date.today()
    if date_from and date_from > today or date_to and date_to > today:
        raise HTTPException(400, "Ngày lọc không được ở tương lai")
    if date_from and date_to and date_from > date_to:
        raise HTTPException(400, "Từ ngày không được sau Đến ngày")


@router.get("/audit", response_model=AuditListOut)
def list_audit(
    q: str | None = None,
    action: str | None = None,
    entity: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=10, le=100),
    db: Session = Depends(get_db),
    _: User = admin_only,
):
    validate_audit_date_range(date_from, date_to)
    query = (
        db.query(AuditLog)
        .outerjoin(User, User.id == AuditLog.actor_id)  # type: ignore
        .outerjoin(UserProfile, UserProfile.user_id == User.id)  # type: ignore
    )
    if action:
        query = query.filter(AuditLog.action == action)  # type: ignore
    if entity:
        query = query.filter(AuditLog.entity == entity)  # type: ignore
    if date_from:
        query = query.filter(func.date(AuditLog.created_at) >= date_from)  # type: ignore
    if date_to:
        query = query.filter(func.date(AuditLog.created_at) <= date_to)  # type: ignore
    if q and q.strip():
        keyword = f"%{q.strip()}%"
        query = query.filter(
            AuditLog.entity_id.ilike(keyword)  # type: ignore
            | func.cast(AuditLog.before_data, String).ilike(keyword)
            | func.cast(AuditLog.after_data, String).ilike(keyword)
            | User.email.ilike(keyword)  # type: ignore
            | UserProfile.full_name.ilike(keyword)  # type: ignore
        )

    total = query.count()
    # AuditLog dùng khai báo SQLAlchemy legacy; chốt kiểu tại biên query để Pylance
    # hiểu các thuộc tính bên dưới là giá trị bản ghi, không phải Column.
    rows = cast(
        list[Any],
        query.order_by(AuditLog.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all(),  # type: ignore
    )
    actor_ids = {row.actor_id for row in rows if row.actor_id}
    actors = {str(user.id): user for user in db.query(User).filter(User.id.in_(actor_ids)).all()} if actor_ids else {}  # type: ignore
    target_ids = []
    for row in rows:
        if row.entity == "users" and row.entity_id:
            try:
                import uuid
                target_ids.append(uuid.UUID(row.entity_id))
            except ValueError:
                pass
    targets = {str(user.id): user for user in db.query(User).filter(User.id.in_(target_ids)).all()} if target_ids else {}  # type: ignore

    items = []
    for row in rows:
        actor = actors.get(str(row.actor_id))
        before = _safe_audit_data(row.before_data)
        after = _safe_audit_data(row.after_data)
        target_user = targets.get(str(row.entity_id))
        target = (
            (target_user.full_name or target_user.email) if target_user else
            (after or {}).get("full_name") or (after or {}).get("email") or
            (before or {}).get("full_name") or (before or {}).get("email") or
            row.entity_id or ""
        )
        description = _audit_description(row.action, row.entity, str(target))
        if (
            row.action == "UPDATE" and row.entity == "users"
            and before and after and before.get("role") != after.get("role")
        ):
            description = f"Đã đổi vai trò {target} từ {before.get('role')} thành {after.get('role')}"
        items.append(AuditOut(
            id=row.id, actor_id=row.actor_id,
            actor_name=actor.full_name if actor else None,
            actor_email=actor.email if actor else None,
            action=row.action, entity=row.entity, entity_id=row.entity_id,
            target_label=str(target),
            description=description,
            before_data=before, after_data=after,
            ip_address=str(row.ip_address) if row.ip_address else None,
            created_at=row.created_at,
        ))
    return AuditListOut(items=items, total=total, page=page, page_size=page_size)

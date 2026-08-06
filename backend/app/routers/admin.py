from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.deps import get_db, require_role
from app.models import (
    User, UserInfo, AuditLog, DocCategory, Document,
)
from app.schemas import (
    AdminUserOut, UpdateRoleIn, AuditOut,
    CategoryIn, DocCategoryOut,
)
from app.services.audit import write_audit
from app.services.slug import tao_slug

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
    query = db.query(User).outerjoin(UserInfo, UserInfo.user_id == User.id)

    tu_khoa = (q or "").strip()
    if tu_khoa:
        kw = f"%{tu_khoa}%"
        if _kiem_tra_unaccent(db):
            dieu_kien = text(
                "unaccent(coalesce(user_info.full_name, '')) ILIKE unaccent(:kw)"
                " OR unaccent(users.email) ILIKE unaccent(:kw)"
            ).bindparams(kw=kw)
        else:
            dieu_kien = text(
                "coalesce(user_info.full_name, '') ILIKE :kw OR users.email ILIKE :kw"
            ).bindparams(kw=kw)
        query = query.filter(dieu_kien)

    return query.order_by(User.updated_at.desc()).all()


@router.get("/users", response_model=list[AdminUserOut])
def list_users(
    q: str | None = Query(None, description="tìm theo họ tên hoặc email"),
    db: Session = Depends(get_db),
    _: User = admin_only,
):
    return search_users(db, q)


@router.patch("/users/{user_id}/role", response_model=AdminUserOut)
def update_role(
    user_id: str, payload: UpdateRoleIn,
    db: Session = Depends(get_db),
    actor: User = admin_only,
):
    user = db.query(User).filter(User.id == user_id).first()  # type: ignore
    if not user:
        raise HTTPException(404, "Không tìm thấy người dùng")

    before = {"role": user.role}
    user.role = payload.role  # type: ignore

    # Auto sync staff_profiles & staff_permissions
    from app.models import StaffProfile, StaffPermission
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
            is_admin = (payload.role == "ADMIN")
            perm = StaffPermission(
                can_manage_users=is_admin,
                can_manage_foods=is_admin,
                can_manage_categories=is_admin,
                can_review_documents=True,
                can_review_plans=True,
                can_review_ai_chat=True,
                can_review_logs=True,
                can_manage_permissions=is_admin,
            )
            sp.permissions = perm
            user.staff_profile = sp
    elif payload.role == "USER" and user.staff_profile:
        db.delete(user.staff_profile)

    write_audit(db, actor.id, "UPDATE", "users", user_id,
                before=before, after={"role": payload.role})  # type: ignore
    db.commit()
    db.refresh(user)
    return user


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
    write_audit(db, actor.id, "DELETE", "users", user_id)
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
@router.get("/audit", response_model=list[AuditOut])
def list_audit(
    limit: int = 100,
    db: Session = Depends(get_db),
    _: User = admin_only,
):
    return db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).all()
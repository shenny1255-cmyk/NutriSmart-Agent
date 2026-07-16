from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.deps import get_db, require_role
from app.models import User, Drug, DrugCountryRule, AuditLog
from app.schemas import (
    AdminUserOut, UpdateRoleIn, DrugIn, DrugOut, DrugRuleIn, AuditOut,
)
from app.services.audit import write_audit

router = APIRouter(prefix="/admin", tags=["admin"])

# Toàn bộ router này chỉ ADMIN vào được
admin_only = Depends(require_role("ADMIN"))


# ---------- Quản lý người dùng ----------
@router.get("/users", response_model=list[AdminUserOut])
def list_users(
    q: str | None = Query(None, description="tìm theo email"),
    db: Session = Depends(get_db),
    _: User = admin_only,
):
    query = db.query(User).filter(User.deleted_at.is_(None))  # type: ignore
    if q:
        query = query.filter(User.email.ilike(f"%{q}%"))
    return query.order_by(User.created_at.desc()).all()


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

    user.deleted_at = datetime.now(timezone.utc)   # type: ignore
    write_audit(db, actor.id, "DELETE", "users", user_id)
    db.commit()


# ---------- Quản lý thuốc ----------
@router.get("/drugs", response_model=list[DrugOut])
def list_drugs(db: Session = Depends(get_db), _: User = admin_only):
    return db.query(Drug).filter(Drug.deleted_at.is_(None)).all()


@router.post("/drugs", response_model=DrugOut, status_code=201)
def create_drug(
    payload: DrugIn,
    db: Session = Depends(get_db),
    actor: User = admin_only,
):
    drug = Drug(**payload.model_dump())
    db.add(drug)
    db.flush()
    write_audit(db, actor.id, "CREATE", "drugs", str(drug.id), after=payload.model_dump())
    db.commit()
    db.refresh(drug)
    return drug


@router.put("/drugs/{drug_id}/rules")
def set_country_rule(
    drug_id: str, payload: DrugRuleIn,
    db: Session = Depends(get_db),
    actor: User = admin_only,
):
    """Đặt trạng thái thuốc theo quốc gia (ALLOWED/RESTRICTED/BANNED)."""
    rule = db.query(DrugCountryRule).filter(
        DrugCountryRule.drug_id == drug_id,
        DrugCountryRule.country_code == payload.country_code,
    ).first()

    if rule:
        before = {"status": rule.status}
        rule.status = payload.status  # type: ignore
        rule.note = payload.note  # type: ignore
        rule.updated_by = actor.id  # type: ignore
    else:
        before = None
        rule = DrugCountryRule(
            drug_id=drug_id, country_code=payload.country_code,
            status=payload.status, note=payload.note, updated_by=actor.id,
        )
        db.add(rule)

    write_audit(db, actor.id, "UPDATE", "drug_country_rules",
                f"{drug_id}:{payload.country_code}",
                before=before, after=payload.model_dump())  # type: ignore
    db.commit()
    return {"message": "Đã cập nhật quy định thuốc theo quốc gia"}


# ---------- Audit logs ----------
@router.get("/audit", response_model=list[AuditOut])
def list_audit(
    limit: int = 100,
    db: Session = Depends(get_db),
    _: User = admin_only,
):
    return db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).all()
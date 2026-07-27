from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
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


def _ensure_default_drugs(db: Session):
    """Dọn dẹp dữ liệu rác từ test và đảm bảo nạp đủ 5 thuốc chuẩn kèm quy định quốc gia."""
    db.execute(text("ALTER TABLE drugs ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;"))
    # Xóa các dòng rác sinh ra do test tự động
    db.execute(text("DELETE FROM drugs WHERE name ILIKE 'Test%';"))

    db.execute(text("""
        INSERT INTO drug_categories (id, name) VALUES (1, 'Thuốc giảm cân'), (2, 'Thuốc cảm sốt')
        ON CONFLICT DO NOTHING;
    """))

    sample_drugs = [
        ('a0000000-0000-0000-0000-000000000001', 1, 'Sibutramine', 'Sibutramine', 'Hỗ trợ giảm cân', 'Tăng huyết áp, nguy cơ đột quỵ, tim mạch', 'Bệnh tim mạch, tăng huyết áp chưa kiểm soát'),
        ('a0000000-0000-0000-0000-000000000002', 1, 'Reductil', 'Sibutramine', 'Giảm cân', 'Tăng nguy cơ biến cố tim mạch', 'Tiền sử bệnh mạch vành, đột quỵ'),
        ('a0000000-0000-0000-0000-000000000003', 1, 'Phentermine', 'Phentermine', 'Giảm thèm ăn', 'Tăng nhịp tim, mất ngủ, nghiện', 'Bệnh tim, tăng áp phổi'),
        ('a0000000-0000-0000-0000-000000000004', 2, 'Pseudoephedrine', 'Pseudoephedrine', 'Giảm sung huyết mũi', 'Tăng huyết áp, hồi hộp', 'Bệnh tăng huyết áp nặng'),
        ('a0000000-0000-0000-0000-000000000005', 2, 'Paracetamol', 'Paracetamol', 'Giảm đau hạ sốt', 'Hại gan khi dùng quá liều', 'Suy gan nặng'),
    ]
    for did, cid, name, active, ind, side, contra in sample_drugs:
        # Nếu chưa có thuốc cùng tên thì chèn
        db.execute(text("""
            INSERT INTO drugs (id, category_id, name, active_ingredient, indications, side_effects, contraindications)
            SELECT :id, :cid, :n, :a, :i, :s, :c
            WHERE NOT EXISTS (SELECT 1 FROM drugs WHERE name = :n);
        """), {"id": did, "cid": cid, "n": name, "a": active, "i": ind, "s": side, "c": contra})

    # Xóa các dòng trùng tên không phải ID chuẩn
    db.execute(text("""
        DELETE FROM drugs WHERE id NOT IN (
            SELECT MIN(id::text)::uuid FROM drugs GROUP BY name
        );
    """))

    sample_rules = [
        ('a0000000-0000-0000-0000-000000000001', 'VN', 'BANNED', 'Bị cấm lưu hành tại Việt Nam do nguy cơ tim mạch và đột quỵ nghiêm trọng.'),
        ('a0000000-0000-0000-0000-000000000002', 'VN', 'BANNED', 'Bị rút giấy phép lưu hành tại Việt Nam do chứa Sibutramine.'),
        ('a0000000-0000-0000-0000-000000000003', 'VN', 'BANNED', 'Cấm sử dụng trong thực phẩm chức năng và thuốc giảm cân không kê đơn tại Việt Nam.'),
        ('a0000000-0000-0000-0000-000000000004', 'VN', 'RESTRICTED', 'Thuốc kê đơn, cần quản lý đặc biệt và có chỉ định của bác sĩ tại Việt Nam.'),
        ('a0000000-0000-0000-0000-000000000005', 'VN', 'ALLOWED', 'Được phép sử dụng theo đúng liều lượng khuyến cáo.'),
    ]
    for did, cc, st, note in sample_rules:
        # Tìm drug_id theo did hoặc theo tên thuốc chuẩn tương ứng
        db.execute(text("""
            INSERT INTO drug_country_rules (drug_id, country_code, status, note)
            SELECT id, :cc, :st, :note FROM drugs WHERE id = :did OR name IN ('Sibutramine', 'Reductil', 'Phentermine', 'Pseudoephedrine', 'Paracetamol')
            ON CONFLICT (drug_id, country_code) DO NOTHING;
        """), {"did": did, "cc": cc, "st": st, "note": note})

    db.commit()


# ---------- Quản lý người dùng ----------
@router.get("/users", response_model=list[AdminUserOut])
def list_users(
    q: str | None = Query(None, description="tìm theo email"),
    db: Session = Depends(get_db),
    _: User = admin_only,
):
    # Dọn dẹp tự động các tài khoản rác sinh ra trong quá trình chạy test
    db.execute(text("DELETE FROM users WHERE email LIKE 'banned_drug_%' OR email LIKE 'rag_%';"))
    db.commit()

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
    _ensure_default_drugs(db)
    return db.query(Drug).all()


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
    """Đặt trạng thái thuốc theo quốc gia (ALLOWED/RESTRICTED/BANNED) và đồng bộ thuốc cùng hoạt chất."""
    default_notes = {
        "BANNED": "Bị cấm lưu hành và sử dụng tại quốc gia này do nguy cơ tim mạch và tác hại nghiêm trọng.",
        "RESTRICTED": "Thuốc bị hạn chế sử dụng (thuốc kê đơn / quản lý đặc biệt), bắt buộc phải có chỉ định của bác sĩ chuyên khoa.",
        "ALLOWED": "Được phép sử dụng theo đúng chỉ định và liều lượng khuyến cáo.",
    }
    new_note = payload.note or default_notes.get(payload.status, "")

    target_drug = db.query(Drug).filter(Drug.id == drug_id).first()
    if not target_drug:
        raise HTTPException(404, "Không tìm thấy thuốc")

    # Tìm tất cả thuốc có cùng hoạt chất để đồng bộ quy định
    drugs_to_update = [target_drug]
    if target_drug.active_ingredient:
        related = db.query(Drug).filter(
            Drug.active_ingredient.ilike(target_drug.active_ingredient),
            Drug.id != target_drug.id,
        ).all()
        drugs_to_update.extend(related)

    for d in drugs_to_update:
        rule = db.query(DrugCountryRule).filter(
            DrugCountryRule.drug_id == d.id,
            DrugCountryRule.country_code == payload.country_code,
        ).first()

        if rule:
            rule.status = payload.status  # type: ignore
            rule.note = new_note  # type: ignore
            rule.updated_by = actor.id  # type: ignore
        else:
            db.add(DrugCountryRule(
                drug_id=d.id, country_code=payload.country_code,
                status=payload.status, note=new_note, updated_by=actor.id,
            ))

    write_audit(db, actor.id, "UPDATE", "drug_country_rules",
                f"{drug_id}:{payload.country_code}",
                before=None, after={"status": payload.status, "note": new_note})  # type: ignore
    db.commit()
    return {"message": "Đã cập nhật và đồng bộ quy định thuốc theo quốc gia"}


# ---------- Audit logs ----------
@router.get("/audit", response_model=list[AuditOut])
def list_audit(
    limit: int = 100,
    db: Session = Depends(get_db),
    _: User = admin_only,
):
    return db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).all()
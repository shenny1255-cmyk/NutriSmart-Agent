from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.deps import get_db, require_role
from app.models import (
    User, Drug, DrugCountryRule, AuditLog, DocCategory, DrugCategory, Document,
)
from app.schemas import (
    AdminUserOut, UpdateRoleIn, DrugIn, DrugOut, DrugRuleIn, AuditOut,
    CategoryIn, DocCategoryOut, DrugCategoryOut,
)
from app.services.audit import write_audit
from app.services.slug import tao_slug

router = APIRouter(prefix="/admin", tags=["admin"])

# Toàn bộ router này chỉ ADMIN vào được
admin_only = Depends(require_role("ADMIN"))
# Riêng danh mục tài liệu thì Chuyên gia cũng cần đọc để gắn khi tải tài liệu lên
expert_or_admin = Depends(require_role("EXPERT", "ADMIN"))


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
    """Danh sách user chưa xóa, lọc theo HỌ TÊN hoặc email khi có từ khóa."""
    query = db.query(User).filter(User.deleted_at.is_(None))  # type: ignore

    tu_khoa = (q or "").strip()
    if tu_khoa:
        kw = f"%{tu_khoa}%"
        if _kiem_tra_unaccent(db):
            dieu_kien = text(
                "unaccent(coalesce(users.full_name, '')) ILIKE unaccent(:kw)"
                " OR unaccent(users.email) ILIKE unaccent(:kw)"
            ).bindparams(kw=kw)
        else:
            dieu_kien = text(
                "coalesce(users.full_name, '') ILIKE :kw OR users.email ILIKE :kw"
            ).bindparams(kw=kw)
        query = query.filter(dieu_kien)

    return query.order_by(User.created_at.desc()).all()


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
        db.query(DocCategory, func.count(Document.id))
        .outerjoin(Document, Document.category_id == DocCategory.id)  # type: ignore
        .group_by(DocCategory.id)
        .order_by(DocCategory.name)
        .all()
    )
    return [
        DocCategoryOut(id=c.id, name=c.name, slug=c.slug, parent_id=c.parent_id, so_tai_lieu=n)
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
    return DocCategoryOut(id=cat.id, name=cat.name, slug=cat.slug, parent_id=cat.parent_id)


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
    return DocCategoryOut(id=cat.id, name=cat.name, slug=cat.slug, parent_id=cat.parent_id)


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


# ---------- Danh mục thuốc ----------

def danh_sach_drug_category(db: Session) -> list[DrugCategoryOut]:
    rows = (
        db.query(DrugCategory, func.count(Drug.id))
        .outerjoin(Drug, (Drug.category_id == DrugCategory.id) & (Drug.deleted_at.is_(None)))  # type: ignore
        .group_by(DrugCategory.id)
        .order_by(DrugCategory.name)
        .all()
    )
    return [DrugCategoryOut(id=c.id, name=c.name, so_thuoc=n) for c, n in rows]


def them_drug_category(db: Session, actor: User, payload: CategoryIn) -> DrugCategoryOut:
    ten = payload.name.strip()
    if db.query(DrugCategory).filter(DrugCategory.name.ilike(ten)).first():  # type: ignore
        raise HTTPException(409, f"Nhóm thuốc '{ten}' đã tồn tại")

    cat = DrugCategory(name=ten)
    db.add(cat)
    db.flush()
    write_audit(db, actor.id, "CREATE", "drug_categories", str(cat.id), after={"name": ten})
    db.commit()
    db.refresh(cat)
    return DrugCategoryOut(id=cat.id, name=cat.name)


def sua_drug_category(db: Session, actor: User, cat_id: int, payload: CategoryIn) -> DrugCategoryOut:
    cat = db.query(DrugCategory).filter(DrugCategory.id == cat_id).first()  # type: ignore
    if not cat:
        raise HTTPException(404, "Không tìm thấy nhóm thuốc")

    ten = payload.name.strip()
    trung = (
        db.query(DrugCategory)
        .filter(DrugCategory.name.ilike(ten), DrugCategory.id != cat_id)  # type: ignore
        .first()
    )
    if trung:
        raise HTTPException(409, f"Nhóm thuốc '{ten}' đã tồn tại")

    truoc = {"name": cat.name}
    cat.name = ten  # type: ignore
    write_audit(db, actor.id, "UPDATE", "drug_categories", str(cat_id),
                before=truoc, after={"name": ten})
    db.commit()
    db.refresh(cat)
    return DrugCategoryOut(id=cat.id, name=cat.name)


def xoa_drug_category(db: Session, actor: User, cat_id: int) -> None:
    """Xóa nhóm thuốc. Thuốc trong nhóm KHÔNG bị xóa — FK là ON DELETE SET NULL."""
    cat = db.query(DrugCategory).filter(DrugCategory.id == cat_id).first()  # type: ignore
    if not cat:
        raise HTTPException(404, "Không tìm thấy nhóm thuốc")

    write_audit(db, actor.id, "DELETE", "drug_categories", str(cat_id), before={"name": cat.name})
    db.delete(cat)
    db.commit()


@router.get("/drug-categories", response_model=list[DrugCategoryOut])
def api_drug_categories(db: Session = Depends(get_db), _: User = admin_only):
    return danh_sach_drug_category(db)


@router.post("/drug-categories", response_model=DrugCategoryOut, status_code=201)
def api_them_drug_category(payload: CategoryIn, db: Session = Depends(get_db), actor: User = admin_only):
    return them_drug_category(db, actor, payload)


@router.patch("/drug-categories/{cat_id}", response_model=DrugCategoryOut)
def api_sua_drug_category(cat_id: int, payload: CategoryIn,
                          db: Session = Depends(get_db), actor: User = admin_only):
    return sua_drug_category(db, actor, cat_id, payload)


@router.delete("/drug-categories/{cat_id}", status_code=204)
def api_xoa_drug_category(cat_id: int, db: Session = Depends(get_db), actor: User = admin_only):
    xoa_drug_category(db, actor, cat_id)


# ---------- Audit logs ----------
@router.get("/audit", response_model=list[AuditOut])
def list_audit(
    limit: int = 100,
    db: Session = Depends(get_db),
    _: User = admin_only,
):
    return db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).all()
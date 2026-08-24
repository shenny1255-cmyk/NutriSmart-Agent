"""Kho bài viết dinh dưỡng — chỉ-đọc, chỉ hiển thị tài liệu APPROVED."""

import re
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.deps import get_db, get_current_user
from app.models import User, Document, DocCategory
from app.schemas import ArticleOut, ArticleCategoryOut, ArticleListOut

router = APIRouter(prefix="/articles", tags=["articles"])


def make_excerpt(raw_text: str | None, max_len: int = 220) -> str:
    """Tạo đoạn giới thiệu ngắn từ raw_text."""
    if not raw_text:
        return ""
    text = re.sub(r"\s+", " ", raw_text).strip()
    if len(text) <= max_len:
        return text
    # Cắt tại ranh giới từ gần nhất không vượt quá max_len
    truncated = text[:max_len]
    last_space = truncated.rfind(" ")
    if last_space > 0:
        truncated = truncated[:last_space]
    return truncated + "…"


@router.get("", response_model=ArticleListOut)
def list_articles(
    q: Optional[str] = Query(None, max_length=100),
    category_id: Optional[int] = Query(None, gt=0),
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=6, le=48),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Danh sách bài viết đã được phê duyệt, có phân trang."""
    base = (
        db.query(Document)
        .filter(Document.status == "APPROVED", Document.deleted_at.is_(None))  # type: ignore
    )

    if q:
        pattern = f"%{q}%"
        # escape ký tự LIKE để tìm kiếm đúng nghĩa đen (%, _)
        escape = lambda s: s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")  # noqa: E731
        pattern = f"%{escape(q)}%"
        base = base.filter(
            (Document.title.ilike(pattern, escape="\\")) | (Document.source_name.ilike(pattern, escape="\\"))  # type: ignore
        )

    if category_id is not None:
        base = base.filter(Document.category_id == category_id)  # type: ignore

    total = base.count()

    docs = (
        base.order_by(
            Document.approved_at.desc().nullslast(),  # type: ignore
            Document.created_at.desc(),  # type: ignore
            Document.id.desc(),  # type: ignore
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    # Lấy danh mục trong một query riêng để tránh N+1
    cat_ids = {d.category_id for d in docs if d.category_id is not None}
    cats = {}
    if cat_ids:
        for c in db.query(DocCategory).filter(DocCategory.id.in_(cat_ids)).all():  # type: ignore
            cats[c.id] = {"id": c.id, "name": c.name, "slug": c.slug}

    items = [
        ArticleOut(
            id=d.id,
            title=d.title,
            excerpt=make_excerpt(d.raw_text),
            source_name=d.source_name,
            source_url=d.source_url,
            category=cats.get(d.category_id),
            approved_at=d.approved_at,
        )
        for d in docs
    ]

    return ArticleListOut(items=items, total=total, page=page, page_size=page_size)


@router.get("/categories", response_model=list[ArticleCategoryOut])
def article_categories(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Danh mục có ít nhất một bài viết đã phê duyệt."""
    rows = (
        db.query(
            DocCategory.id,
            DocCategory.name,
            DocCategory.slug,
            func.count(Document.id).label("article_count"),
        )
        .join(Document, Document.category_id == DocCategory.id)  # type: ignore
        .filter(Document.status == "APPROVED", Document.deleted_at.is_(None))  # type: ignore
        .group_by(DocCategory.id, DocCategory.name, DocCategory.slug)
        .order_by(DocCategory.name)
        .all()
    )
    return [
        ArticleCategoryOut(id=r.id, name=r.name, slug=r.slug, article_count=r.article_count)
        for r in rows
    ]

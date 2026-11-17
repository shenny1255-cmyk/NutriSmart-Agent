"""Tra cứu Bảng thành phần thực phẩm Việt Nam (Viện Dinh dưỡng 2007) - kế hoạch ĐATN v2, GĐ1.

Nguồn sự thật cho kcal/macro: AI chỉ ước lượng gram, còn kcal = gram × giá trị/100 g tra ở đây.
Dữ liệu gốc: data/food_composition_vn2007.csv (trích từ PDF chính thức bằng
scripts/import_vn_fct.py, nhóm duyệt qua PR). Bảng food_composition trong Postgres là bản sao
để tìm kiếm nhanh, tự nạp khi rỗng.
"""
from __future__ import annotations

import csv
import logging
from functools import lru_cache
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import FoodComposition

logger = logging.getLogger(__name__)

CSV_PATH = Path(__file__).resolve().parents[2] / "data" / "food_composition_vn2007.csv"
REVIEW_STATUSES = ("CHUA_DUYET", "DA_DUYET", "CAN_SUA")
SOURCE_URL = "https://www.fao.org/fileadmin/templates/food_composition/documents/pdf/VTN_FCT_2007.pdf"

NUMERIC = ("waste_pct", "energy_kcal", "protein_g", "fat_g", "carb_g", "fiber_g", "sugar_g",
           "water_g", "sodium_mg", "cholesterol_mg", "purine_mg")
# Chỉ số quy đổi theo khối lượng (không gồm % thải bỏ hay nước)
SCALED = ("energy_kcal", "protein_g", "fat_g", "carb_g", "fiber_g", "sugar_g",
          "sodium_mg", "cholesterol_mg", "purine_mg")


def _f(v: str | None) -> float | None:
    v = (v or "").strip()
    return float(v) if v else None


@lru_cache(maxsize=1)
def _load_csv_cached() -> tuple[dict, ...]:
    rows = []
    with CSV_PATH.open(encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            row: dict = {
                "code": r["code"].strip(),
                "name_vi": r["name_vi"].strip(),
                "name_en": r["name_en"].strip() or None,
                "food_group": r["food_group"].strip() or None,
                "book_page": int(r["book_page"]) if r["book_page"].strip() else None,
                "check_note": r["check_note"].strip() or None,
                "review_status": r["review_status"].strip() or "CHUA_DUYET",
            }
            for k in NUMERIC:
                row[k] = _f(r.get(k))
            row["source"] = (f"Viện Dinh dưỡng (2007), Bảng thành phần thực phẩm Việt Nam, "
                             f"tr. {row['book_page']}, mã {row['code']}")
            rows.append(row)
    return tuple(rows)


def load_csv() -> list[dict]:
    return [dict(r) for r in _load_csv_cached()]


def scale(row, grams: float, *, as_purchased: bool = False) -> dict:
    """Quy đổi giá trị/100 g sang khẩu phần `grams`.

    as_purchased=True: grams là khối lượng cả phần thải bỏ (vỏ, xương) → trừ waste_pct trước.
    Chỉ số thiếu số liệu giữ None, không đoán 0.
    """
    get = row.get if isinstance(row, dict) else (lambda k, d=None: getattr(row, k, d))
    edible = float(grams)
    if as_purchased and get("waste_pct"):
        edible *= 1 - float(get("waste_pct")) / 100
    out: dict = {"grams": grams, "edible_grams": round(edible, 1)}
    for k in SCALED:
        v = get(k)
        out[k] = None if v is None else round(float(v) * edible / 100, 2)
    return out


def sync_from_csv(db: Session) -> int:
    """Upsert toàn bộ CSV vào Postgres (chạy lại an toàn). Trả số dòng."""
    rows = load_csv()
    if not rows:
        return 0
    stmt = insert(FoodComposition).values(rows)
    cols = {c: stmt.excluded[c] for c in rows[0] if c != "code"}
    cols["updated_at"] = func.now()
    db.execute(stmt.on_conflict_do_update(index_elements=["code"], set_=cols))
    db.commit()
    return len(rows)


def ensure_loaded(db: Session) -> None:
    """Bảng rỗng (DB mới chạy migration 29) → tự nạp từ CSV."""
    if db.scalar(select(func.count()).select_from(FoodComposition)) == 0:
        n = sync_from_csv(db)
        logger.info("Đã nạp %s dòng Bảng thành phần thực phẩm từ %s", n, CSV_PATH.name)


def search(db: Session, q: str | None, limit: int = 20) -> list[FoodComposition]:
    """Tìm theo tên, không phân biệt dấu ("gao te" → "Gạo tẻ"). Khớp đầu tên xếp trước,
    sau đó theo độ giống trigram."""
    ensure_loaded(db)
    query = select(FoodComposition)
    q = (q or "").strip()
    if q:
        name = func.f_unaccent(func.lower(FoodComposition.name_vi))
        needle = func.f_unaccent(func.lower(q))
        exact = func.lower(FoodComposition.name_vi)
        query = (query.where(name.like(func.concat("%", needle, "%")))
                 # gõ có dấu "cá" → "Cá chép" trước "Cà bát"
                 .order_by(exact.like(func.concat(func.lower(q), "%")).desc(),
                           name.like(func.concat(needle, "%")).desc(),
                           func.similarity(name, needle).desc(),
                           FoodComposition.name_vi))
    else:
        query = query.order_by(FoodComposition.code)
    return list(db.scalars(query.limit(limit)))


def get(db: Session, code: str) -> FoodComposition | None:
    ensure_loaded(db)
    return db.get(FoodComposition, code)

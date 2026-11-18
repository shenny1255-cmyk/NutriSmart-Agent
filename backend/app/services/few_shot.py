"""Kho few-shot có kiểm duyệt cho ước lượng khẩu phần (kế hoạch ĐATN v2, mục 2.1 - GĐ3).

Vòng lặp HITL: người dùng sửa gram → Expert duyệt → ca đã duyệt vào kho → lần quét món tương tự
được chèn ví dụ vào prompt. Mô hình không đổi trọng số, chỉ có ngữ cảnh được bổ sung.

Nguyên tắc: truy hồi KHÔNG bao giờ làm hỏng phân tích ảnh. Ollama tắt thì dùng trigram theo tên
món; lỗi bất kỳ thì trả danh sách rỗng và giữ kết quả ban đầu.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models import FewShotExample, User, VisionFeedback
from app.services import portion
from app.services.ollama_client import OllamaError, get_embedding

log = logging.getLogger("nutrismart.few_shot")

TOP_K = 3
# Ngưỡng khởi điểm, cần hiệu chỉnh lại trên bộ ảnh cân thật khi đo learning curve.
MIN_NAME_SIMILARITY = 0.45
MIN_COSINE = 0.82
EMBED_TIMEOUT_SECONDS = 5.0
MAX_NAME_CHARS = 80

_UNSAFE_CHARS = re.compile(r"[\x00-\x1f\x7f{}\[\]<>`\"\\]")

_SEARCH_SQL = text("""
    SELECT id FROM (
        SELECT id, created_at,
               similarity(f_unaccent(lower(food_name)), f_unaccent(lower(:name))) AS name_score,
               CASE WHEN CAST(:qvec AS vector) IS NULL OR embedding IS NULL THEN 0
                    ELSE 1 - (embedding <=> CAST(:qvec AS vector)) END AS cosine
        FROM few_shot_examples
        WHERE is_active
    ) scored
    WHERE name_score >= :min_name OR cosine >= :min_cos
    ORDER BY GREATEST(name_score, cosine) DESC, created_at DESC
    LIMIT :k
""")


def clean_name(value: str) -> str:
    """Tên đi vào prompt của người khác nên bỏ ký tự có thể phá cấu trúc dữ liệu."""
    return re.sub(r"\s+", " ", _UNSAFE_CHARS.sub(" ", value or "")).strip()[:MAX_NAME_CHARS]


def _embed(value: str) -> list[float] | None:
    try:
        return get_embedding(value, timeout=EMBED_TIMEOUT_SECONDS)
    except (OllamaError, OSError) as e:
        log.info("Không tạo được embedding few-shot, dùng trigram: %s", e)
        return None


def _vector_literal(vector: list[float] | None) -> str | None:
    return None if vector is None else "[" + ",".join(str(v) for v in vector) + "]"


def example_components(components: list[dict]) -> list[dict]:
    out = [{"name": clean_name(c["name"]), "grams": round(float(c["grams"]), 1), "fct_code": c.get("fct_code")}
           for c in components]
    if not out or any(not c["name"] for c in out):
        raise ValueError("Ca duyệt phải có ít nhất một thành phần hợp lệ")
    return out


def approve(db: Session, feedback: VisionFeedback, expert: User, components: list[dict] | None = None,
            note: str | None = None) -> FewShotExample:
    """Duyệt ca sửa vào kho. Expert có thể chỉnh gram; kcal luôn do server tính. Không commit."""
    known = list(feedback.final_components or []) + list(feedback.predicted_components or [])
    final = portion.recalculate(components, known) if components else list(feedback.final_components or [])
    if not final:
        raise ValueError("Ca sửa không có dữ liệu khẩu phần")
    name = clean_name(feedback.food_name)
    example = FewShotExample(
        feedback_id=feedback.id, food_name=name, components=example_components(final),
        total_kcal=portion.totals(final)["energy_kcal"], embedding=_embed(name), approved_by=expert.id,
    )
    db.add(example)
    _mark_reviewed(feedback, expert, "APPROVED", note)
    return example


def reject(feedback: VisionFeedback, expert: User, note: str | None = None) -> None:
    _mark_reviewed(feedback, expert, "REJECTED", note)


def _mark_reviewed(feedback: VisionFeedback, expert: User, status: str, note: str | None) -> None:
    feedback.review_status = status
    feedback.reviewed_by = expert.id
    feedback.reviewed_at = datetime.now(timezone.utc)
    feedback.review_note = (note or "").strip() or None


def retrieve(db: Session, food_name: str | None, k: int = TOP_K) -> list[FewShotExample]:
    """Ví dụ đang hoạt động của món tương tự, giống nhất trước."""
    name = clean_name(food_name or "")
    if not name:
        return []
    try:
        if not db.query(FewShotExample.id).filter(FewShotExample.is_active.is_(True)).first():  # type: ignore
            return []
        ids = db.execute(_SEARCH_SQL, {
            "name": name, "qvec": _vector_literal(_embed(name)), "min_name": MIN_NAME_SIMILARITY,
            "min_cos": MIN_COSINE, "k": k,
        }).scalars().all()
        rows = {r.id: r for r in db.query(FewShotExample).filter(FewShotExample.id.in_(ids)).all()}  # type: ignore
        return [rows[i] for i in ids if i in rows]
    except Exception as e:  # noqa: BLE001
        db.rollback()
        log.warning("Không truy hồi được few-shot: %s", e)
        return []


def prompt_examples(examples: list[FewShotExample]) -> str:
    """Chỉ đưa tên món, tên thành phần và gram vào prompt, dạng dữ liệu JSON."""
    return json.dumps([
        {"food_name": e.food_name,
         "components": [{"name": c["name"], "grams": c["grams"]} for c in e.components]}
        for e in examples
    ], ensure_ascii=False)

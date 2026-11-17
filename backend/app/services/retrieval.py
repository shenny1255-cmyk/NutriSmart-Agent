"""Truy hồi tri thức (RAG) cho Trợ lý AI.

Tìm các đoạn tài liệu (doc_chunks) liên quan nhất tới câu hỏi bằng **hybrid search**:
kết hợp độ tương đồng vector (cosine, chỉ mục HNSW) với độ tương đồng chuỗi
(trigram, chỉ mục GIN). Hai điểm đều nằm trong khoảng 0..1 nên cộng có trọng số được.

Nguyên tắc: retrieval KHÔNG bao giờ làm hỏng cuộc trò chuyện. Ollama chết hay kho
tri thức rỗng thì trả về danh sách rỗng, chat vẫn trả lời dựa trên hồ sơ người dùng.
"""

import logging
from dataclasses import dataclass
from functools import lru_cache

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.ollama_client import get_embedding, OllamaError

log = logging.getLogger("nutrismart.retrieval")

# Trọng số hybrid: ưu tiên ngữ nghĩa (vector), trigram bổ trợ khi trùng thuật ngữ.
# Ban đầu chọn 0.7 theo kinh nghiệm; thực nghiệm quét w=0.0→1.0 trên 59 câu hỏi
# (GĐ2 ĐATN) cho thấy w=0.9 đạt nDCG@5=0.701 so với w=0.7 đạt 0.674, chênh lệch
# có ý nghĩa thống kê (paired bootstrap 10.000 lần, hiệu +0.028, CI95%=[+0.001;+0.070]).
# w=1.0 chỉ hơn w=0.9 +0.001 (không có ý nghĩa thống kê).
# Giữ 0.1 trigram để không mất hoàn toàn khả năng khớp tên riêng/thuật ngữ đặc thù.
W_VECTOR = 0.9
W_TRIGRAM = 0.1

# Ngưỡng lọc: dưới ngưỡng này coi như không liên quan.
# Hiệu chỉnh theo F1 trên bộ 59 câu hỏi GĐ2, TÍNH VỚI w=0.9 (ngưỡng phụ thuộc trọng số:
# tăng w thì điểm cả kho tăng theo, nên ngưỡng 0.41 hiệu chỉnh cho w=0.7 không dùng lại được).
# Với w=0.9: ngưỡng 0.51 cho P=0.786, R=0.759, F1=0.772 (6/30 câu trích dẫn sai);
# giữ 0.41 thì P=0.553, 21/30 câu trích dẫn sai. Đổi W_VECTOR phải chạy lại sweep để chọn lại ngưỡng.
MIN_SCORE = 0.51

SNIPPET_CHARS = 200


@dataclass
class Hit:
    chunk_id: int
    content: str
    score: float
    doc_title: str
    source_url: str | None


_SEARCH_SQL = text("""
    SELECT c.id,
           c.content,
           d.title       AS doc_title,
           d.source_url  AS source_url,
           (:w_vec * (1 - (c.embedding <=> CAST(:qvec AS vector)))
            + :w_trg * similarity(c.content, :q)) AS score
    FROM doc_chunks c
    JOIN documents d ON d.id = c.document_id
    WHERE c.embedding IS NOT NULL
      AND d.status = 'APPROVED'
      AND d.deleted_at IS NULL
    ORDER BY score DESC
    LIMIT :k
""")

_HAS_SEARCHABLE_CHUNKS_SQL = text("""
    SELECT EXISTS (
        SELECT 1
        FROM doc_chunks c
        JOIN documents d ON d.id = c.document_id
        WHERE c.embedding IS NOT NULL
          AND d.status = 'APPROVED'
          AND d.deleted_at IS NULL
    )
""")


def _has_searchable_chunks(db: Session) -> bool | None:
    """Kiểm tra nhanh kho RAG; None nghĩa là không kiểm tra được."""
    try:
        return bool(db.execute(_HAS_SEARCHABLE_CHUNKS_SQL).scalar())
    except Exception as e:  # noqa: BLE001 - RAG không được làm hỏng chat
        log.warning("[RAG] Không kiểm tra được kho tài liệu (%s) - tiếp tục truy hồi", e)
        return None


@lru_cache(maxsize=128)
def _query_embedding(query: str) -> list[float]:
    """Tái sử dụng embedding của câu hỏi lặp lại trong cùng process."""
    return get_embedding(query)


def search_chunks(db: Session, query: str, k: int = 5) -> list[Hit]:
    """Trả về tối đa k đoạn liên quan nhất tới `query`, đã lọc theo ngưỡng MIN_SCORE."""
    if _has_searchable_chunks(db) is False:
        return []

    try:
        qvec = _query_embedding(query)
    except OllamaError as e:
        log.warning("[RAG] Không tạo được embedding cho câu hỏi (%s) - bỏ qua truy hồi", e)
        return []

    try:
        rows = db.execute(_SEARCH_SQL, {
            "qvec": str(qvec),          # pgvector nhận literal dạng '[0.1,0.2,...]'
            "q": query,
            "k": k,
            "w_vec": W_VECTOR,
            "w_trg": W_TRIGRAM,
        }).mappings().all()
    except Exception as e:  # noqa: BLE001 - lỗi truy vấn không được làm hỏng chat
        log.warning("[RAG] Truy vấn hybrid search thất bại (%s) - bỏ qua truy hồi", e)
        return []

    return [
        Hit(
            chunk_id=r["id"],
            content=r["content"],
            score=float(r["score"]),
            doc_title=r["doc_title"],
            source_url=r["source_url"],
        )
        for r in rows
        if r["score"] is not None and float(r["score"]) >= MIN_SCORE
    ]


def render_context_block(hits: list[Hit]) -> str:
    """Ghép các đoạn tìm được thành khối ngữ cảnh đánh số cho prompt.

    Không có đoạn nào → chuỗi rỗng, để caller không phải rẽ nhánh.
    """
    if not hits:
        return ""

    lines = [
        "",
        "Tài liệu tham khảo (chỉ dùng khi liên quan tới câu hỏi, "
        "trích dẫn theo số thứ tự [1], [2]… nếu có dùng):",
    ]
    for i, h in enumerate(hits, start=1):
        lines.append(f"[{i}] {h.doc_title}: {h.content}")
    return "\n".join(lines)


def to_citation(hit: Hit) -> dict:
    """Chuyển Hit sang dạng UI đang đọc: {title, url, snippet}."""
    snippet = hit.content.strip()
    if len(snippet) > SNIPPET_CHARS:
        snippet = snippet[:SNIPPET_CHARS].rstrip() + "…"
    return {"title": hit.doc_title, "url": hit.source_url, "snippet": snippet}

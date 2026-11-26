"""Khôi phục dấu tiếng Việt cho câu hỏi gõ không dấu trước khi truy hồi RAG.

bge-m3 hiểu kém tiếng Việt không dấu: trên bộ 59 câu GĐ2, bỏ dấu làm cosine của đoạn đúng
giảm từ 0.62 xuống 0.41 và hit@5 từ 22/51 còn 1/51 (ngưỡng MIN_SCORE 0.51 chặn hết).
Đổi trọng số trigram sang so khớp không dấu chỉ đạt 5/51 vì trigram chỉ chiếm 0.1 điểm.

Cách làm: học n-gram (1-3 từ) từ chính kho tài liệu đã duyệt + danh mục món ăn, mỗi cụm không
dấu ánh xạ tới dạng có dấu xuất hiện nhiều nhất; khớp tham lam cụm dài trước. Chạy nội bộ, không
gọi LLM. Trên cùng bộ 59 câu đã bỏ dấu: đúng 89.8% số từ, hit@5 trở lại 22/51, câu lạc đề vẫn 0/8.
Từ không có trong kho giữ nguyên.
"""
from __future__ import annotations

import re
import threading
import unicodedata
from collections import Counter, defaultdict

from sqlalchemy import text
from sqlalchemy.orm import Session

MAX_N = 3
_WORD = re.compile(r"\w+", re.UNICODE)

Index = list[dict[str, str]]   # index[n][cụm không dấu] = cụm có dấu phổ biến nhất

_CORPUS_VERSION_SQL = text("""
    SELECT count(*), coalesce(max(c.id), 0), (SELECT count(*) FROM foods)
    FROM doc_chunks c JOIN documents d ON d.id = c.document_id
    WHERE d.status = 'APPROVED' AND d.deleted_at IS NULL
""")
_CORPUS_SQL = text("""
    SELECT c.content FROM doc_chunks c JOIN documents d ON d.id = c.document_id
    WHERE d.status = 'APPROVED' AND d.deleted_at IS NULL
    UNION ALL
    SELECT name FROM foods
""")

_lock = threading.Lock()
_cache: tuple[tuple, Index] | None = None


def strip_accents(s: str) -> str:
    s = unicodedata.normalize("NFD", s).replace("đ", "d").replace("Đ", "D")
    return unicodedata.normalize("NFC", "".join(ch for ch in s if unicodedata.category(ch) != "Mn"))


def has_diacritics(s: str) -> bool:
    return strip_accents(s) != unicodedata.normalize("NFC", s)


def _tokens(s: str) -> list[str]:
    return _WORD.findall(unicodedata.normalize("NFC", s).lower())


def build_index(texts) -> Index:
    counts = [defaultdict(Counter) for _ in range(MAX_N + 1)]
    for t in texts:
        toks = _tokens(t or "")
        for n in range(1, MAX_N + 1):
            for i in range(len(toks) - n + 1):
                gram = " ".join(toks[i:i + n])
                counts[n][strip_accents(gram)][gram] += 1
    return [{k: c.most_common(1)[0][0] for k, c in level.items()} for level in counts]


def restore(query: str, index: Index) -> str:
    toks, out, i = _tokens(query), [], 0
    while i < len(toks):
        for n in range(MAX_N, 0, -1):
            key = " ".join(toks[i:i + n])
            if len(toks[i:i + n]) == n and key in index[n]:
                out.append(index[n][key])
                i += n
                break
        else:
            out.append(toks[i])
            i += 1
    return " ".join(out)


def corpus_index(db: Session) -> Index:
    """Chỉ mục dựng từ kho hiện tại; tự dựng lại khi có tài liệu/món ăn mới."""
    global _cache
    version = tuple(db.execute(_CORPUS_VERSION_SQL).one())
    with _lock:
        if _cache is None or _cache[0] != version:
            _cache = (version, build_index(r[0] for r in db.execute(_CORPUS_SQL)))
        return _cache[1]


def restore_query(db: Session, query: str) -> str:
    """Câu đã có dấu → giữ nguyên. Câu không dấu → khôi phục theo kho tài liệu."""
    if has_diacritics(query):
        return query
    restored = restore(query, corpus_index(db))
    return restored or query

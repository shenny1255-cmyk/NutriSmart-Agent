"""Unit tests cho retrieval: khối ngữ cảnh và cách nuốt lỗi embedding."""

import pytest

from app.services import retrieval
from app.services.retrieval import Hit, render_context_block, search_chunks
from app.services.ollama_client import OllamaError


def _hit(i: int) -> Hit:
    return Hit(
        chunk_id=i,
        content=f"Nội dung tài liệu số {i}",
        score=0.9 - i * 0.1,
        doc_title=f"Tài liệu {i}",
        source_url=f"https://example.com/{i}",
    )


def test_context_block_numbers_each_source():
    block = render_context_block([_hit(1), _hit(2)])
    assert "[1]" in block and "[2]" in block
    assert "Tài liệu 1" in block and "Tài liệu 2" in block
    assert "Nội dung tài liệu số 1" in block


def test_context_block_empty_when_no_hits():
    # Không có tài liệu liên quan → không chèn gì vào prompt
    assert render_context_block([]) == ""


def test_search_returns_empty_when_embedding_fails(monkeypatch):
    """Ollama/bge-m3 hỏng thì chat vẫn phải chạy — retrieval chỉ trả về rỗng."""
    def boom(*a, **k):
        raise OllamaError("ollama down")

    monkeypatch.setattr(retrieval, "get_embedding", boom)
    # db không được đụng tới vì lỗi xảy ra trước khi truy vấn
    assert search_chunks(None, "câu hỏi bất kỳ") == [] # type: ignore

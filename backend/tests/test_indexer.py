"""Unit tests cho module indexer (Chunking & Embedding pipeline)."""

from app.services.indexer import split_text


def test_split_text_empty():
    assert split_text("") == []
    assert split_text(None) == []


def test_split_text_short():
    text = "Bài viết ngắn dưới 500 ký tự."
    chunks = split_text(text, chunk_size=500, chunk_overlap=100)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_split_text_long_splits_properly():
    # Tạo văn bản dài khoảng 1200 ký tự
    paragraph = "HƯỚNG DẪN DINH DƯỠNG CÁ NHÂN HÓA. " * 35
    chunks = split_text(paragraph, chunk_size=500, chunk_overlap=100)

    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk) <= 500

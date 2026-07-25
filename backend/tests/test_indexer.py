"""Unit tests cho module indexer (Chunking & Embedding pipeline)."""

from app.services.indexer import split_text


def test_split_text_empty():
    assert split_text("") == []
    assert split_text(None) == []


def test_split_text_short():
    text = "Bài viết ngắn dưới 500 ký tự và có rất ít từ."
    # Tên của hàm chỉ ra chunk_size=500 tokens. 
    # Văn bản này chỉ có 12 từ (tokens), nên chắc chắn trả về 1 chunk duy nhất.
    chunks = split_text(text, chunk_size=500, chunk_overlap=100)
    assert len(chunks) == 1
    assert chunks[0] == text.strip()


def test_split_text_long_splits_properly():
    # Tạo văn bản dài khoảng 900 từ (tokens)
    word = "NutriSmart"
    words = [f"{word}_{i}" for i in range(900)]
    text = " ".join(words)
    
    # Cắt với chunk_size = 500 tokens, overlap = 100 tokens
    chunks = split_text(text, chunk_size=500, chunk_overlap=100)

    # Tổng 900 từ:
    # - Chunk 1: từ index 0 đến 500 -> 500 từ.
    # - Chunk tiếp theo bắt đầu ở start = 400 (500 - 100).
    # - Token còn lại từ 400 đến 900 là 500 từ. Nên chunk 2 có 500 từ.
    # Kêt quả nhận được là 2 chunks.
    assert len(chunks) == 2
    for chunk in chunks:
        tokens_in_chunk = chunk.split()
        assert len(tokens_in_chunk) == 500

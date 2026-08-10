import pytest
from app.services.indexer import split_text

def test_split_text_short_document():
    text = "Đây là một bài viết ngắn về dinh dưỡng. Bài viết chỉ có vài câu."
    chunks = split_text(text, chunk_size=800)
    assert len(chunks) == 1
    assert chunks[0] == text.strip()


def test_split_text_semantic_paragraphs():
    # Tạo văn bản nhiều đoạn văn dài với tiêu đề H2/H3
    p1 = "## 1. Nguyên tắc dinh dưỡng chung\n" + " ".join(["Từ"] * 400)
    p2 = "\n\n## 2. Các thực phẩm nên dùng\n" + " ".join(["Thực_phẩm"] * 450)
    p3 = "\n\n## 3. Lời khuyên vận động\n" + " ".join(["Vận_động"] * 300)
    text = p1 + p2 + p3

    chunks = split_text(text, chunk_size=500, chunk_overlap=50)
    assert len(chunks) >= 2
    # Các đoạn chunk phải bảo tồn nội dung tiêu đề và không bị cắt vụn
    assert any("1. Nguyên tắc dinh dưỡng chung" in c for c in chunks)
    assert any("2. Các thực phẩm nên dùng" in c for c in chunks)


def test_split_text_with_context():
    doc_title = "Chế độ ăn cho người tiểu đường"
    doc_source = "suckhoedoisong.vn"
    raw_text = "Nội dung bài viết chi tiết về chế độ ăn tiểu đường. " + " ".join(["Chi_tiết"] * 600)

    chunks = split_text(raw_text, chunk_size=500, title=doc_title, source_name=doc_source)
    assert len(chunks) > 0
    assert chunks[0].startswith(f"[Tài liệu: {doc_title} | Nguồn: {doc_source}]")

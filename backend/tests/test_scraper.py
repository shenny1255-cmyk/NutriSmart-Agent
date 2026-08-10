import pytest
from app.services.scraper import HTMLTextExtractor, extract_source_name, _kiem_tra_trang_rac, fetch_and_parse_url

def test_extract_source_name():
    assert extract_source_name("https://suckhoedoisong.vn/che-do-an-123.htm") == "suckhoedoisong.vn"
    assert extract_source_name("https://www.vinmec.com/vie/bai-viet/abc") == "vinmec.com"
    assert extract_source_name("invalid-url") == "Nguồn web"


def test_html_text_extractor_article_body():
    html = """
    <html>
        <head><title>Chế độ ăn cho người tiểu đường</title></head>
        <body>
            <header><nav>Menu 1 | Menu 2</nav></header>
            <div class="sidebar">Quảng cáo side</div>
            <article class="detail-content">
                <h1>Chế độ ăn cho người tiểu đường type 2</h1>
                <p>Người bệnh tiểu đường nên tuân thủ chế độ ăn giảm tinh bột nhanh, tăng cường chất xơ từ rau xanh.</p>
                <p>Nên bổ sung đầy đủ nước và theo dõi chỉ số đường huyết định kỳ theo hướng dẫn của bác sĩ chuyên khoa.</p>
            </article>
            <footer>Bản quyền 2026</footer>
        </body>
    </html>
    """
    parser = HTMLTextExtractor()
    parser.feed(html)
    title = parser.get_title()
    text = parser.get_text()

    assert title == "Chế độ ăn cho người tiểu đường"
    assert "Chế độ ăn cho người tiểu đường type 2" in text
    assert "Menu 1" not in text
    assert "Bản quyền 2026" not in text


def test_kiem_tra_trang_rac_raises():
    with pytest.raises(ValueError, match="trang lỗi"):
        _kiem_tra_trang_rac("https://example.com/404", "404 - Không tìm thấy trang", "Nội dung ngắn")

    with pytest.raises(ValueError, match="chỉ có"):
        _kiem_tra_trang_rac("https://example.com/bai-viet", "Bài viết chuẩn", "Nội dung chỉ có 500 ký tự")

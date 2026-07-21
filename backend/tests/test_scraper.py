"""Unit tests cho module Medical Scraper."""

from app.services.scraper import HTMLTextExtractor, extract_source_name


def test_html_text_extractor_removes_ignored_tags():
    sample_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Hướng Dẫn Ăn Uống Cho Bệnh Nhân Tiểu Đường</title>
        <style> body { color: red; } </style>
    </head>
    <body>
        <nav> <a href="#">Trang chủ</a> </nav>
        <h1>Dinh Dưỡng Dành Cho Bệnh Nhân Đái Tháo Đường Típ 2</h1>
        <p>Bệnh nhân cần tăng cường chất xơ từ rau củ và hạn chế tinh bột tinh chế.</p>
        <script> alert('Hello'); </script>
        <footer> Bản quyền thuộc về Bộ Y tế </footer>
    </body>
    </html>
    """

    parser = HTMLTextExtractor()
    parser.feed(sample_html)

    title = parser.get_title()
    text = parser.get_text()

    assert "Hướng Dẫn Ăn Uống" in title
    assert "Dinh Dưỡng Dành Cho Bệnh Nhân Đái Tháo Đường Típ 2" in text
    assert "Bệnh nhân cần tăng cường chất xơ" in text

    # Các phần trong thẻ ngó lơ không được xuất hiện
    assert "color: red" not in text
    assert "Trang chủ" not in text
    assert "alert" not in text
    assert "Bản quyền" not in text


def test_extract_source_name():
    assert extract_source_name("https://moh.gov.vn/tin-tuc") == "moh.gov.vn"
    assert extract_source_name("https://www.who.int/news-room") == "who.int"
    assert extract_source_name("invalid-url") == "Nguồn web"

"""Dịch vụ cào dữ liệu y khoa (Medical Data Scraper).

Thu thập nội dung bài viết hướng dẫn dinh dưỡng/y tế từ các URL web uy tín,
bóc tách tiêu đề và văn bản thuần, sau đó lưu vào DB ở trạng thái PENDING.
"""

from html.parser import HTMLParser
import logging
from urllib.parse import urlparse
import httpx
from sqlalchemy.orm import Session

from app.models import Document

logger = logging.getLogger(__name__)


class HTMLTextExtractor(HTMLParser):
    """Bóc tách văn bản thuần từ HTML, loại bỏ thẻ script, style, nav, footer."""

    def __init__(self):
        super().__init__()
        self.text_parts = []
        self.title_parts = []
        self.in_title = False
        self.ignore_tag = False
        self.ignored_tags = {"script", "style", "nav", "footer", "header", "noscript", "svg"}

    def handle_starttag(self, tag, attrs):
        tag_lower = tag.lower()
        if tag_lower == "title":
            self.in_title = True
        elif tag_lower in self.ignored_tags:
            self.ignore_tag = True

    def handle_endtag(self, tag):
        tag_lower = tag.lower()
        if tag_lower == "title":
            self.in_title = False
        elif tag_lower in self.ignored_tags:
            self.ignore_tag = False

    def handle_data(self, data):
        data_cleaned = data.strip()
        if not data_cleaned:
            return

        if self.in_title:
            self.title_parts.append(data_cleaned)
        elif not self.ignore_tag:
            self.text_parts.append(data_cleaned)

    def get_title(self) -> str:
        return " ".join(self.title_parts).strip()

    def get_text(self) -> str:
        return "\n".join(self.text_parts).strip()


def extract_source_name(url: str) -> str:
    """Rút gọn tên nguồn từ tên miền URL (ví dụ: moh.gov.vn -> moh.gov.vn)."""
    try:
        domain = urlparse(url).netloc
        if domain.startswith("www."):
            domain = domain[4:]
        return domain or "Nguồn web"
    except Exception:
        return "Nguồn web"


import ssl


def get_ssl_context():
    """Tạo SSL Context tương thích với các máy chủ y tế sử dụng SSL/TLS phiên bản cũ."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        ctx.set_ciphers("DEFAULT@SECLEVEL=1")
    except Exception:
        pass
    return ctx


def fetch_and_parse_url(url: str, timeout: float = 15.0) -> dict:
    """Tải nội dung trang web từ URL và bóc tách tiêu đề + văn bản thuần."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    try:
        ssl_ctx = get_ssl_context()
        resp = httpx.get(url, headers=headers, timeout=timeout, follow_redirects=True, verify=ssl_ctx)
        resp.raise_for_status()
        html_content = resp.text
    except Exception as e:
        logger.error(f"[Scraper] Lỗi khi tải URL {url}: {e}")
        raise ValueError(f"Không thể tải nội dung từ URL {url}: {e}") from e

    parser = HTMLTextExtractor()
    parser.feed(html_content)

    title = parser.get_title()
    raw_text = parser.get_text()
    source_name = extract_source_name(url)

    if not title:
        # Nếu không có thẻ title, lấy 50 ký tự đầu tiên của text
        title = raw_text[:60].replace("\n", " ").strip() if raw_text else url

    if not raw_text or len(raw_text) < 50:
        raise ValueError(f"Nội dung thu thập từ URL {url} quá ngắn hoặc không tìm thấy văn bản hợp lệ.")

    return {
        "title": title,
        "source_name": source_name,
        "source_url": url,
        "raw_text": raw_text,
    }


def crawl_urls(urls: list[str], db: Session, uploaded_by_id=None) -> dict:
    """Cào danh sách URL, kiểm tra chống trùng lặp và lưu vào DB ở trạng thái PENDING."""
    inserted_docs = []
    skipped_count = 0
    errors = []

    for url in urls:
        url_clean = url.strip()
        if not url_clean:
            continue

        # 1. Kiểm tra trùng lặp đường link trong cơ sở dữ liệu
        existing = db.query(Document).filter(
            Document.source_url == url_clean,
            Document.deleted_at.is_(None)
        ).first()

        if existing:
            logger.info(f"[Scraper] Đã tồn tại tài liệu với URL {url_clean}, bỏ qua.")
            skipped_count += 1
            continue

        # 2. Cào bài viết
        try:
            parsed_data = fetch_and_parse_url(url_clean)
        except Exception as e:
            logger.error(f"[Scraper] Lỗi cào {url_clean}: {e}")
            errors.append({"url": url_clean, "error": str(e)})
            continue

        # 3. Tạo tài liệu mới trạng thái PENDING
        doc = Document(
            title=parsed_data["title"],
            source_name=parsed_data["source_name"],
            source_url=parsed_data["source_url"],
            raw_text=parsed_data["raw_text"],
            status="PENDING",
            uploaded_by=uploaded_by_id,
        )
        db.add(doc)
        inserted_docs.append(doc)

    if inserted_docs:
        db.commit()
        for doc in inserted_docs:
            db.refresh(doc)

    return {
        "inserted": len(inserted_docs),
        "skipped": skipped_count,
        "errors": errors,
        "documents": inserted_docs,
    }


PRESET_SOURCES = {
    "moh": {
        "name": "Báo Sức khỏe & Đời sống - Bộ Y tế (suckhoedoisong.vn)",
        "urls": [
            "https://suckhoedoisong.vn/dinh-duong-cho-nguoi-tieu-duong-169230510103551522.htm",
            "https://suckhoedoisong.vn/che-do-an-uong-cho-nguoi-cao-huyet-ap-169230412154512411.htm",
            "https://suckhoedoisong.vn/dinh-duong-cho-nguoi-roi-loan-lipid-mau-169230515162345112.htm",
            "https://suckhoedoisong.vn/khuyen-nghi-luong-muoi-cho-nguoi-truong-thanh-169230601091234567.htm",
            "https://suckhoedoisong.vn/vai-tro-cua-chat-xo-trong-bua-an-hang-ngay-169230605112233445.htm",
        ]
    },
    "who": {
        "name": "Viện Dinh dưỡng Quốc gia (viendinhduong.vn)",
        "urls": [
            "http://viendinhduong.vn/vi/dinh-duong-tiet-che/huong-dan-dinh-duong-cho-nguoi-tieu-duong.html",
            "http://viendinhduong.vn/vi/dinh-duong-tiet-che/dinh-duong-cho-nguoi-tang-huyet-ap.html",
            "http://viendinhduong.vn/vi/tin-tuc---su-kien-noi-bat/nhu-cau-dinh-duong-khuyen-nghi-cho-nguoi-viet-nam.html",
        ]
    }
}


def crawl_preset_sources(source_key: str = "moh", limit: int = 10, db: Session = None, uploaded_by_id=None) -> dict:
    """Cào bài viết tự động theo nguồn uy tín có sẵn (vd: Bộ Y tế 'moh', WHO 'who', hoặc 'all')."""
    target_urls = []

    if source_key == "all":
        for src in PRESET_SOURCES.values():
            target_urls.extend(src["urls"])
    elif source_key in PRESET_SOURCES:
        target_urls = PRESET_SOURCES[source_key]["urls"]
    else:
        raise ValueError(f"Nguồn '{source_key}' không hợp lệ. Các nguồn hỗ trợ: moh, who, all")

    target_urls = target_urls[:limit]
    return crawl_urls(target_urls, db, uploaded_by_id=uploaded_by_id)


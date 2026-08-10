"""Dịch vụ cào dữ liệu y khoa bất đồng bộ (Async Medical Data Scraper).

Thu thập nội dung bài viết hướng dẫn dinh dưỡng/y tế từ các URL web uy tín,
bóc tách tiêu đề và văn bản thuần (ưu tiên phần thân bài viết), sau đó lưu vào DB ở trạng thái PENDING.
"""

import asyncio
from html.parser import HTMLParser
import logging
import ssl
from urllib.parse import urlparse
import httpx
from sqlalchemy.orm import Session

from app.models import Document

logger = logging.getLogger(__name__)

# Các thẻ tự đóng (void tags) không có thẻ đóng trong HTML5 — không được push vào ignore_stack
VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr"
}


class HTMLTextExtractor(HTMLParser):
    """Bóc tách văn bản thuần từ HTML, loại bỏ thẻ script, style, nav, footer, sidebar, ads."""

    def __init__(self):
        super().__init__()
        self.text_parts = []
        self.title_parts = []
        self.in_title = False
        self.ignored_tags = {
            "script", "style", "nav", "footer", "header", "noscript", "svg", "aside", "form"
        }
        self.ignored_classes = {
            "sidebar", "ad", "ads", "advertisement", "comment", "related", "footer", "header", "nav"
        }
        self.ignore_stack = []

    def handle_starttag(self, tag, attrs):
        tag_lower = tag.lower()
        if tag_lower in VOID_TAGS:
            return

        if tag_lower == "title":
            self.in_title = True
            return

        is_ignored = tag_lower in self.ignored_tags
        if not is_ignored:
            attr_dict = dict(attrs)
            class_val = attr_dict.get("class", "").lower()
            id_val = attr_dict.get("id", "").lower()
            
            if any(ignored in class_val.split() for ignored in self.ignored_classes) or \
               any(ignored in id_val.split() for ignored in self.ignored_classes):
                is_ignored = True

        if is_ignored or self.ignore_stack:
            self.ignore_stack.append(tag_lower)

    def handle_endtag(self, tag):
        tag_lower = tag.lower()
        if tag_lower in VOID_TAGS:
            return

        if tag_lower == "title":
            self.in_title = False
            return

        if self.ignore_stack and self.ignore_stack[-1] == tag_lower:
            self.ignore_stack.pop()

    def handle_data(self, data):
        data_cleaned = data.strip()
        if not data_cleaned:
            return

        if self.in_title:
            self.title_parts.append(data_cleaned)
        elif not self.ignore_stack:
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


_TIEU_DE_RAC = (
    "trang không tồn tại", "không tìm thấy", "page not found", "404",
    "lỗi truy cập", "access denied",
)
_DO_DAI_TOI_THIEU = 1500      # bài viết y khoa thật luôn dài hơn mức này


def _kiem_tra_trang_rac(url: str, title: str, raw_text: str, url_cuoi: str | None = None) -> None:
    """Ném ValueError nếu trang cào về là 404/trang chủ chứ không phải bài viết."""
    tieu_de = (title or "").lower()
    for mau in _TIEU_DE_RAC:
        if mau in tieu_de:
            raise ValueError(f"URL {url} trả về trang lỗi ('{title}'), không phải bài viết.")

    if url_cuoi:
        duong_dan_goc = urlparse(url).path.strip("/")
        duong_dan_cuoi = urlparse(url_cuoi).path.strip("/")
        if duong_dan_goc and not duong_dan_cuoi:
            raise ValueError(
                f"URL {url} bị chuyển hướng về trang chủ ({url_cuoi}) — bài viết không còn tồn tại."
            )

    if len(raw_text) < _DO_DAI_TOI_THIEU:
        raise ValueError(
            f"Nội dung từ {url} chỉ có {len(raw_text)} ký tự — nhiều khả năng là "
            "trang lỗi hoặc trang chủ, không phải bài viết."
        )


async def fetch_and_parse_url_async(url: str, timeout: float = 15.0, max_retries: int = 3) -> dict:
    """Tải bất đồng bộ nội dung trang web từ URL với cơ chế retry exponential backoff."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    ssl_ctx = get_ssl_context()
    last_err = None

    for attempt in range(1, max_retries + 1):
        try:
            async with httpx.AsyncClient(headers=headers, timeout=timeout, follow_redirects=True, verify=ssl_ctx) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                html_content = resp.text
                url_cuoi = str(resp.url)
                break
        except Exception as e:
            last_err = e
            logger.warning(f"[AsyncScraper] Lỗi thử lần {attempt}/{max_retries} cho URL {url}: {e}")
            if attempt < max_retries:
                await asyncio.sleep(0.5 * (2 ** (attempt - 1)))
    else:
        logger.error(f"[AsyncScraper] Thất bại toàn bộ {max_retries} lần thử với URL {url}: {last_err}")
        raise ValueError(f"Không thể tải nội dung từ URL {url}: {last_err}") from last_err

    parser = HTMLTextExtractor()
    parser.feed(html_content)

    title = parser.get_title()
    raw_text = parser.get_text()
    source_name = extract_source_name(url)

    if not title:
        title = raw_text[:60].replace("\n", " ").strip() if raw_text else url

    if not raw_text or len(raw_text) < 50:
        raise ValueError(f"Nội dung thu thập từ URL {url} quá ngắn hoặc không tìm thấy văn bản hợp lệ.")

    _kiem_tra_trang_rac(url, title, raw_text, url_cuoi)

    return {
        "title": title,
        "source_name": source_name,
        "source_url": url,
        "raw_text": raw_text,
    }


def fetch_and_parse_url(url: str, timeout: float = 15.0) -> dict:
    """Wrapper đồng bộ tương thích ngược cho fetch_and_parse_url_async."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
            }
            ssl_ctx = get_ssl_context()
            resp = httpx.get(url, headers=headers, timeout=timeout, follow_redirects=True, verify=ssl_ctx)
            resp.raise_for_status()
            html_content = resp.text
            url_cuoi = str(resp.url)
            parser = HTMLTextExtractor()
            parser.feed(html_content)
            title = parser.get_title()
            raw_text = parser.get_text()
            source_name = extract_source_name(url)
            if not title:
                title = raw_text[:60].replace("\n", " ").strip() if raw_text else url
            if not raw_text or len(raw_text) < 50:
                raise ValueError(f"Nội dung thu thập từ URL {url} quá ngắn hoặc không tìm thấy văn bản hợp lệ.")
            _kiem_tra_trang_rac(url, title, raw_text, url_cuoi)
            return {
                "title": title,
                "source_name": source_name,
                "source_url": url,
                "raw_text": raw_text,
            }
        else:
            return loop.run_until_complete(fetch_and_parse_url_async(url, timeout=timeout))
    except RuntimeError:
        return asyncio.run(fetch_and_parse_url_async(url, timeout=timeout))


async def crawl_urls_async(urls: list[str], db: Session, uploaded_by_id=None) -> dict:
    """Cào danh sách URL bất đồng bộ song song, kiểm tra chống trùng lặp và lưu vào DB ở trạng thái PENDING."""
    clean_urls = [u.strip() for u in urls if u and u.strip()]
    if not clean_urls:
        return {"inserted": 0, "skipped": 0, "errors": [], "documents": []}

    inserted_docs = []
    skipped_count = 0
    errors = []

    existing_urls = set(
        row[0] for row in db.query(Document.source_url)
        .filter(Document.source_url.in_(clean_urls), Document.deleted_at.is_(None))
        .all()
    )

    urls_to_fetch = []
    for url in clean_urls:
        if url in existing_urls:
            skipped_count += 1
        else:
            urls_to_fetch.append(url)

    tasks = [fetch_and_parse_url_async(url) for url in urls_to_fetch]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for url, res in zip(urls_to_fetch, results):
        if isinstance(res, Exception):
            logger.error(f"[AsyncScraper] Lỗi cào {url}: {res}")
            errors.append({"url": url, "error": str(res)})
        else:
            doc = Document(
                title=res["title"],
                source_name=res["source_name"],
                source_url=res["source_url"],
                raw_text=res["raw_text"],
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


def crawl_urls(urls: list[str], db: Session, uploaded_by_id=None) -> dict:
    """Wrapper đồng bộ cho crawl_urls_async."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            inserted_docs = []
            skipped_count = 0
            errors = []
            for url in urls:
                url_clean = url.strip()
                if not url_clean:
                    continue
                existing = db.query(Document).filter(Document.source_url == url_clean, Document.deleted_at.is_(None)).first()
                if existing:
                    skipped_count += 1
                    continue
                try:
                    parsed_data = fetch_and_parse_url(url_clean)
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
                except Exception as e:
                    errors.append({"url": url_clean, "error": str(e)})
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
        else:
            return loop.run_until_complete(crawl_urls_async(urls, db, uploaded_by_id))
    except RuntimeError:
        return asyncio.run(crawl_urls_async(urls, db, uploaded_by_id))


PRESET_SOURCES = {
    "moh": {
        "name": "Báo Sức khỏe & Đời sống - Bộ Y tế (suckhoedoisong.vn)",
        "urls": [
            "https://suckhoedoisong.vn/che-do-an-trong-benh-dai-thao-duong-169240302134740875.htm",
            "https://www.vinmec.com/vie/bai-viet/che-do-an-cho-nguoi-benh-gout-vi",
            "https://www.vinmec.com/vie/bai-viet/che-do-cho-nguoi-benh-tang-huyet-ap-vi",
            "https://www.vinmec.com/vie/bai-viet/tim-hieu-ve-che-do-dash-cho-benh-nhan-tang-huyet-ap-vi",
            "https://www.vinmec.com/vie/bai-viet/dinh-duong-trong-benh-roi-loan-lipid-mau-vi",
        ]
    },
    "vinmec": {
        "name": "Hệ thống Y tế Vinmec (vinmec.com)",
        "urls": [
            "https://www.vinmec.com/vie/bai-viet/che-do-an-cho-nguoi-benh-gout-vi",
            "https://www.vinmec.com/vie/bai-viet/che-do-cho-nguoi-benh-tang-huyet-ap-vi",
            "https://www.vinmec.com/vie/bai-viet/tim-hieu-ve-che-do-dash-cho-benh-nhan-tang-huyet-ap-vi",
            "https://www.vinmec.com/vie/bai-viet/dinh-duong-trong-benh-roi-loan-lipid-mau-vi",
        ]
    },
    "who": {
        "name": "Hệ thống Y tế Vinmec (vinmec.com)",
        "urls": [
            "https://www.vinmec.com/vie/bai-viet/che-do-an-cho-nguoi-benh-gout-vi",
        ]
    }
}


BI_DANH_NGUON = {"who": "vinmec"}


async def crawl_preset_sources_async(source_key: str = "moh", limit: int = 10, db: Session | None = None, uploaded_by_id=None) -> dict:
    """Cào bài viết tự động theo nguồn uy tín có sẵn (bất đồng bộ)."""
    target_urls = []
    source_key = BI_DANH_NGUON.get(source_key, source_key)

    if source_key == "all":
        for src in PRESET_SOURCES.values():
            target_urls.extend(src["urls"])
    elif source_key in PRESET_SOURCES:
        target_urls = PRESET_SOURCES[source_key]["urls"]
    else:
        ho_tro = ", ".join([*PRESET_SOURCES, *BI_DANH_NGUON, "all"])
        raise ValueError(f"Nguồn '{source_key}' không hợp lệ. Các nguồn hỗ trợ: {ho_tro}")

    target_urls = target_urls[:limit]
    return await crawl_urls_async(target_urls, db, uploaded_by_id=uploaded_by_id)


def crawl_preset_sources(source_key: str = "moh", limit: int = 10, db: Session | None = None, uploaded_by_id=None) -> dict:
    """Wrapper đồng bộ cho crawl_preset_sources_async."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            target_urls = []
            sk = BI_DANH_NGUON.get(source_key, source_key)
            if sk == "all":
                for src in PRESET_SOURCES.values():
                    target_urls.extend(src["urls"])
            elif sk in PRESET_SOURCES:
                target_urls = PRESET_SOURCES[sk]["urls"]
            else:
                ho_tro = ", ".join([*PRESET_SOURCES, *BI_DANH_NGUON, "all"])
                raise ValueError(f"Nguồn '{source_key}' không hợp lệ. Các nguồn hỗ trợ: {ho_tro}")
            target_urls = target_urls[:limit]
            return crawl_urls(target_urls, db, uploaded_by_id=uploaded_by_id)
        else:
            return loop.run_until_complete(crawl_preset_sources_async(source_key, limit, db, uploaded_by_id))
    except RuntimeError:
        return asyncio.run(crawl_preset_sources_async(source_key, limit, db, uploaded_by_id))

"""Bóc văn bản từ file tài liệu do Admin/Chuyên gia tải lên.

Chỉ nhận định dạng văn bản thuần và PDF — đủ cho tài liệu y khoa, và tránh phụ thuộc
thư viện nặng. Ảnh chụp tài liệu đi đường Vision chứ không qua đây.
"""
import io
import logging

logger = logging.getLogger(__name__)

DUOI_FILE_HO_TRO = (".txt", ".md", ".pdf")
KICH_THUOC_TOI_DA = 10 * 1024 * 1024   # 10 MB


class LoaiFileKhongHoTro(ValueError):
    """File không thuộc DUOI_FILE_HO_TRO."""


def doc_text_tu_file(ten_file: str, noi_dung: bytes) -> str:
    """Trả về văn bản thuần của file; ném LoaiFileKhongHoTro nếu đuôi file lạ."""
    ten = (ten_file or "").lower()

    if ten.endswith(".pdf"):
        return _doc_pdf(noi_dung)

    if ten.endswith((".txt", ".md")):
        # Tài liệu tiếng Việt hay được lưu ở nhiều bảng mã; thử lần lượt
        for bang_ma in ("utf-8", "utf-16", "cp1258", "latin-1"):
            try:
                return noi_dung.decode(bang_ma).strip()
            except UnicodeDecodeError:
                continue
        return noi_dung.decode("utf-8", errors="replace").strip()

    raise LoaiFileKhongHoTro(
        f"Chỉ hỗ trợ {', '.join(DUOI_FILE_HO_TRO)} — file '{ten_file}' không đọc được."
    )


def _doc_pdf(noi_dung: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(noi_dung))
    cac_trang = []
    for i, trang in enumerate(reader.pages):
        try:
            cac_trang.append(trang.extract_text() or "")
        except Exception as e:
            logger.warning("Không bóc được chữ ở trang %s của PDF: %s", i + 1, e)
    return "\n".join(cac_trang).strip()

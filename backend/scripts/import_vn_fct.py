"""Số hóa Bảng thành phần thực phẩm Việt Nam (Viện Dinh dưỡng, NXB Y học 2007).

Nguồn dữ liệu: bản PDF chính thức do FAO lưu trữ
    https://www.fao.org/fileadmin/templates/food_composition/documents/pdf/VTN_FCT_2007.pdf
Mỗi trang chi tiết = 1 thực phẩm, giá trị cho 100 g phần ăn được. Tên tiếng Việt trong PDF
dùng font TCVN3 (ABC) cũ nên phải giải mã sang Unicode.

Script KHÔNG tự đoán số liệu, chỉ trích xuất:
- Giá trị số nguyên 1 chữ số bị dính với mã nguồn ("mg 01" = 0, nguồn 1). Token như "31" không
  có cột nguồn riêng là mơ hồ (3 hay 31) → để trống và ghi chú cho nhóm tra lại trang gốc.
- Mỗi dòng được kiểm tra chéo bằng công thức Atwater (4·P + 9·L + 4·G ≈ năng lượng).

Chạy từ backend/ (cần pypdf, đã có trong requirements.txt):
    PYTHONUTF8=1 ./.venv/Scripts/python.exe scripts/import_vn_fct.py <đường dẫn VTN_FCT_2007.pdf>
Kết quả: data/food_composition_vn2007.csv
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
OUT = BACKEND / "data" / "food_composition_vn2007.csv"
SOURCE_URL = "https://www.fao.org/fileadmin/templates/food_composition/documents/pdf/VTN_FCT_2007.pdf"

GROUPS = {
    1: "Ngũ cốc và sản phẩm chế biến", 2: "Khoai củ và sản phẩm chế biến",
    3: "Hạt, quả giàu đạm, béo và sản phẩm chế biến", 4: "Rau, quả, củ dùng làm rau",
    5: "Quả chín", 6: "Dầu, mỡ, bơ", 7: "Thịt và sản phẩm chế biến",
    8: "Thủy sản và sản phẩm chế biến", 9: "Trứng và sản phẩm chế biến",
    10: "Sữa và sản phẩm chế biến", 11: "Đồ hộp", 12: "Đồ ngọt (đường, bánh, mứt, kẹo)",
    13: "Gia vị, nước chấm", 14: "Nước giải khát, bia, rượu",
}

# TCVN3 (TCVN 5712:1993) byte → Unicode. pypdf trả byte theo Latin-1 nên key là ký tự Latin-1.
_TCVN3 = {
    0xA1: "Ă", 0xA2: "Â", 0xA3: "Ê", 0xA4: "Ô", 0xA5: "Ơ", 0xA6: "Ư", 0xA7: "Đ",
    0xA8: "ă", 0xA9: "â", 0xAA: "ê", 0xAB: "ô", 0xAC: "ơ", 0xAD: "ư", 0xAE: "đ",
    0xB5: "à", 0xB6: "ả", 0xB7: "ã", 0xB8: "á", 0xB9: "ạ", 0xBB: "ằ", 0xBC: "ẳ", 0xBD: "ẵ",
    0xBE: "ắ", 0xC6: "ặ", 0xC7: "ầ", 0xC8: "ẩ", 0xC9: "ẫ", 0xCA: "ấ", 0xCB: "ậ", 0xCC: "è",
    0xCE: "ẻ", 0xCF: "ẽ", 0xD0: "é", 0xD1: "ẹ", 0xD2: "ề", 0xD3: "ể", 0xD4: "ễ", 0xD5: "ế",
    0xD6: "ệ", 0xD7: "ì", 0xD8: "ỉ", 0xDC: "ĩ", 0xDD: "í", 0xDE: "ị", 0xDF: "ò", 0xE1: "ỏ",
    0xE2: "õ", 0xE3: "ó", 0xE4: "ọ", 0xE5: "ồ", 0xE6: "ổ", 0xE7: "ỗ", 0xE8: "ố", 0xE9: "ộ",
    0xEA: "ờ", 0xEB: "ở", 0xEC: "ỡ", 0xED: "ớ", 0xEE: "ợ", 0xEF: "ù", 0xF1: "ủ", 0xF2: "ũ",
    0xF3: "ú", 0xF4: "ụ", 0xF5: "ừ", 0xF6: "ử", 0xF7: "ữ", 0xF8: "ứ", 0xF9: "ự", 0xFA: "ỳ",
    0xFB: "ỷ", 0xFC: "ỹ", 0xFD: "ý", 0xFE: "ỵ",
}
_TCVN3_MAP = {chr(k): v for k, v in _TCVN3.items()}
_TCVN3_MAP["μ"] = "à"   # pypdf đôi khi trả µ (0xB5) thành chữ Hy Lạp μ
_TCVN3_MAP["−"] = "ư"   # 0xAD (soft hyphen) bị map thành dấu trừ


def tcvn3_to_unicode(s: str) -> str:
    out = re.sub(r"\s+", " ", "".join(_TCVN3_MAP.get(ch, ch) for ch in s)).strip()
    # Chữ hoa có dấu nằm ở font TCVN3 riêng (.VnTimeH) nên giải mã ra chữ thường: "ớt" → "Ớt"
    return out[:1].upper() + out[1:]


def _num(s: str | None) -> float | None:
    if s is None or s.strip() in {"", "-"}:
        return None
    try:
        return float(s)
    except ValueError:
        return None


_DEC = r"(-|\d+\.\d+|\d+)"
_INT = r"(-|\d+ \d\b|\d+)"

# Macro luôn có phần thập phân và cột nguồn tách bằng dấu cách: "Protein g 8.6 1".
_MACROS = {
    "water_g": r"Nước \(Water ?\) g ",
    "protein_g": r"\nProtein g ",
    "fat_g": r"Lipid \(Fat\) g ",
    "carb_g": r"Glucid \(Carbohydrate\) g ",
    "fiber_g": r"Celluloza \(Fiber\) g ",
    "sugar_g": r"Đường tổng số \(Sugar\) g ",
}
_INTS = {
    "sodium_mg": r"Natri \(Sodium\) mg ",
    "cholesterol_mg": r"Cholesterol mg ",
    "purine_mg": r"Purin mg ",
}


def parse_int_token(tok: str) -> tuple[float | None, bool]:
    """→ (giá trị, mơ_hồ). "01" = 0 (nguồn 1); "282 1" = 282; "31" không có cột nguồn là mơ hồ.

    Đã kiểm tra trên toàn bộ PDF: giá trị có cột nguồn riêng không bao giờ có 1 chữ số, tức là
    mọi giá trị 1 chữ số đều bị dính mã nguồn → "31" có thể là 3 (nguồn 1) hoặc 31 (không nguồn).
    """
    tok = tok.strip()
    if tok == "-":
        return None, False
    if " " in tok:
        return float(tok.split()[0]), False
    if len(tok) == 2 and tok[0] == "0":
        return 0.0, False
    return None, True


def _macro_token(tok: str) -> float | None:
    if "." not in tok and len(tok) == 2 and tok[0] == "0":
        return 0.0   # "g 03" = 0, nguồn 3
    return _num(tok)


def _names(text: str) -> tuple[str | None, str]:
    """Tên VN/EN. Hai kiểu trang: tên ngay sau nhãn, hoặc nhãn rỗng và tên nằm đầu trang
    ("Nhéng STT: 359" / "Silk worm M· sè: 7081")."""
    m_vi = re.search(r"Tªn thùc phÈm \(Vietnamese\):[ \t]*(.*)", text)
    m_en = re.search(r"Tªn tiÕng Anh \(English\):[ \t]*(.*)", text)
    vi = re.sub(r"\s*STT: *\d+\s*$", "", m_vi.group(1).strip() if m_vi else "")
    en = re.sub(r"\s*M· sè: *\d+\s*$", "", m_en.group(1).strip() if m_en else "")
    if not vi:
        m = re.search(r"^(.*?)\s*STT: *\d+", text, re.M)
        vi = m.group(1).strip() if m else ""
    if not en:
        m = re.search(r"^(.*?)\s*M· sè: *\d+", text, re.M)
        en = m.group(1).strip() if m else ""
    return (tcvn3_to_unicode(vi) if vi else None), re.sub(r"\s+", " ", en).strip()


def parse_page(text: str) -> dict | None:
    m_code = re.search(r"M· sè: *(\d{4,5})", text)
    if not m_code:
        return None
    name_vi, name_en = _names(text)
    if not name_vi:
        return None
    m_waste = re.search(r"Th¶i bá \(%\): *" + _DEC, text)
    m_energy = re.search(r"Năng lượng \(Energy ?\) KCal " + _DEC, text)
    m_page = re.search(r"\n\s*(\d{1,3})\s*$", text)
    code = m_code.group(1)
    row = {
        "code": code,
        "name_vi": name_vi,
        "name_en": name_en,
        "food_group": GROUPS.get(int(code[:-3]), ""),
        "waste_pct": _num(m_waste.group(1)) if m_waste else None,
        "energy_kcal": _num(m_energy.group(1)) if m_energy else None,
        "ambiguous": [],
    }
    for key, pat in _MACROS.items():
        m = re.search(pat + _DEC, text)
        row[key] = _macro_token(m.group(1)) if m else None
    for key, pat in _INTS.items():
        m = re.search(pat + _INT, text)
        val, amb = parse_int_token(m.group(1)) if m else (None, False)
        row[key] = val
        if amb:
            row["ambiguous"].append(f"{key.split('_')[0]} '{m.group(1)}'")  # type: ignore[union-attr]
    row["book_page"] = int(m_page.group(1)) if m_page else None
    return row


def atwater_check(row: dict, tol: float = 0.15) -> str:
    """'' nếu năng lượng khớp 4P+9L+4G trong ±15% (tối thiểu ±10 kcal); ngược lại ghi chú."""
    e = row.get("energy_kcal")
    if e is None:
        return "thiếu năng lượng"
    p, l, g = (row.get(k) or 0.0 for k in ("protein_g", "fat_g", "carb_g"))
    calc = 4 * p + 9 * l + 4 * g
    if abs(calc - e) > max(tol * e, 10):
        # Đồ uống có cồn: 7 kcal/g cồn không nằm trong P/L/G nên lệch là bình thường
        return f"Atwater lệch: 4P+9L+4G = {calc:.0f} vs bảng {e:.0f}"
    return ""


# Số liệu trích đúng từ PDF nhưng bất thường so với tham chiếu khác → nhóm đối chiếu sách in.
KNOWN_ISSUES = {
    "10001": "natri 380 mg/100 g cao bất thường với sữa tươi (USDA FDC 746782: 43 mg), có thể in nhầm",
}


def check_note(row: dict) -> str:
    notes = [atwater_check(row), KNOWN_ISSUES.get(row["code"], "")]
    if row.get("ambiguous"):
        notes.append("số mơ hồ, tra trang gốc: " + ", ".join(row["ambiguous"]))
    return "; ".join(n for n in notes if n)


FIELDS = ["code", "name_vi", "name_en", "food_group", "waste_pct", "energy_kcal", "protein_g",
          "fat_g", "carb_g", "fiber_g", "sugar_g", "water_g", "sodium_mg", "cholesterol_mg",
          "purine_mg", "book_page", "check_note", "review_status"]


def extract(pdf_path: str) -> list[dict]:
    import pypdf

    rows, seen = [], set()
    for page in pypdf.PdfReader(pdf_path).pages:
        row = parse_page(page.extract_text() or "")
        if row and row["code"] not in seen:
            seen.add(row["code"])
            row["check_note"] = check_note(row)
            row["review_status"] = "CHUA_DUYET"
            rows.append(row)
    return rows


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    rows = extract(sys.argv[1])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: ("" if r.get(k) is None else r[k]) for k in FIELDS})
    flagged = [r for r in rows if r["check_note"]]
    print(f"Đã trích {len(rows)} thực phẩm → {OUT}")
    print(f"Cần nhóm xem lại: {len(flagged)} dòng")


if __name__ == "__main__":
    main()

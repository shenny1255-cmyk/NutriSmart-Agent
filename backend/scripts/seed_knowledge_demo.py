"""Nạp dữ liệu mẫu cho 4 màn Tri thức và Chuyên gia: danh mục, bài viết, ca sửa khẩu phần.

Chạy từ backend/ (cần Postgres; nên bật Ollama với model bge-m3 để bài viết có vector cho RAG):
    PYTHONUTF8=1 ./.venv/Scripts/python.exe scripts/seed_knowledge_demo.py
    PYTHONUTF8=1 ./.venv/Scripts/python.exe scripts/seed_knowledge_demo.py --no-crawl   # không cào bài chờ duyệt

Chạy lại nhiều lần không tạo trùng: danh mục theo slug, bài viết theo URL, ca sửa theo mã cố định.

Nguồn gốc dữ liệu:
- Chỉ dùng bài báo thật (Vinmec, Sức khỏe & Đời sống, vnpa.moh.gov.vn), cào từ trang gốc bằng bộ cào của hệ
  thống nên tiêu đề, nội dung và URL là thật. Script không tự soạn nội dung y khoa.
- Ca sửa khẩu phần là dữ liệu giả lập, không có ảnh và không gắn bữa ăn trong Nhật ký.
"""
from __future__ import annotations

import argparse
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.database import SessionLocal  # noqa: E402
from app.models import DocCategory, DocChunk, Document, FewShotExample, User, VisionFeedback  # noqa: E402
from app.services import few_shot, portion  # noqa: E402
from app.services.indexer import run_indexing_pipeline  # noqa: E402
from app.services.ollama_client import OllamaError, get_embedding  # noqa: E402
from app.services.scraper import crawl_urls, fetch_and_parse_url  # noqa: E402

SEED_NS = uuid.UUID("0b8f7a52-3c1e-4f4a-9d36-5e2c8a1b7f10")
EXPERT_EMAIL = "expert1@nutrismart.vn"

CATEGORIES = [
    ("Hướng dẫn dinh dưỡng", "huong-dan-dinh-duong"),
    ("Nghiên cứu y khoa", "nghien-cuu-y-khoa"),
    ("Dinh dưỡng bệnh lý", "dinh-duong-benh-ly"),
]

PENDING_URLS = [
    "https://www.vinmec.com/vie/bai-viet/cach-uong-khoa-hoc-giam-can-hieu-qua-vi",
    "https://www.vinmec.com/vie/bai-viet/18-cach-dua-tren-khoa-hoc-de-giam-con-doi-va-them-vi",
    "https://vnpa.moh.gov.vn/tang-cuong-vi-chat-dinh-duong-vao-thuc-pham-trong-bua-an-hang-ngay/",
]

# Bài thật đã có nguồn gốc rõ ràng: (URL bài gốc, slug danh mục). Bài đã có trong DB thì chỉ gắn danh mục
# nếu đang trống; chưa có thì cào từ trang gốc rồi duyệt như Expert bấm Duyệt.
APPROVED_REAL = [
    ("https://suckhoedoisong.vn/che-do-an-trong-benh-dai-thao-duong-169240302134740875.htm", "dinh-duong-benh-ly"),
    ("https://www.vinmec.com/vie/bai-viet/che-do-an-cho-nguoi-benh-gout-vi", "dinh-duong-benh-ly"),
    ("https://www.vinmec.com/vie/bai-viet/che-do-cho-nguoi-benh-tang-huyet-ap-vi", "dinh-duong-benh-ly"),
    ("https://www.vinmec.com/vie/bai-viet/dinh-duong-trong-benh-roi-loan-lipid-mau-vi", "dinh-duong-benh-ly"),
    ("https://www.vinmec.com/vie/bai-viet/ke-hoach-kieng-tot-nhat-cho-nguoi-thieu-mau-vi", "dinh-duong-benh-ly"),
    ("https://www.vinmec.com/vie/bai-viet/nen-gi-bo-sung-sat-cho-nguoi-thieu-mau-thieu-sat-vi", "dinh-duong-benh-ly"),
    ("https://www.vinmec.com/vie/bai-viet/trao-nguoc-da-day-thuc-quan-nen-an-gi-va-kieng-an-gi-vi", "dinh-duong-benh-ly"),
    ("https://www.vinmec.com/vie/bai-viet/7-thuc-pham-giup-giam-trao-nguoc-axit-vi", "dinh-duong-benh-ly"),
    ("https://www.vinmec.com/vie/bai-viet/che-do-de-giam-can-lanh-manh-vi", "huong-dan-dinh-duong"),
    ("https://www.vinmec.com/vie/bai-viet/tai-sao-chung-ta-can-uong-2-lit-nuoc-moi-ngay-vi", "huong-dan-dinh-duong"),
    ("https://www.vinmec.com/vie/bai-viet/uong-nuoc-bao-nhieu-la-du-vi", "huong-dan-dinh-duong"),
    # DASH là chế độ ăn hình thành từ các thử nghiệm lâm sàng nên tạm xếp vào nhóm này; nhóm có thể đổi lại.
    ("https://www.vinmec.com/vie/bai-viet/tim-hieu-ve-che-do-dash-cho-benh-nhan-tang-huyet-ap-vi", "nghien-cuu-y-khoa"),
]

# Ca sửa khẩu phần giả lập: AI đoán, người dùng sửa; ca APPROVED có thêm số chuyên gia chốt.
CORRECTIONS = [
    {"key": "pho-bo", "user": "user1@nutrismart.vn", "food": "Phở bò",
     "ai": [("Bánh phở", 150), ("Thịt bò", 60), ("Hành lá", 10)],
     "user_grams": [("Bánh phở", 190), ("Thịt bò", 80), ("Hành lá", 10)]},
    {"key": "com-tam", "user": "user2@nutrismart.vn", "food": "Cơm tấm sườn trứng",
     "ai": [("Cơm trắng", 180), ("Sườn nướng", 90), ("Trứng gà", 50), ("Dưa chuột", 30)],
     "user_grams": [("Cơm trắng", 220), ("Sườn nướng", 110), ("Trứng gà", 50), ("Dưa chuột", 30)]},
    {"key": "bun-cha", "user": "user1@nutrismart.vn", "food": "Bún chả",
     "ai": [("Bún", 150), ("Thịt lợn", 90), ("Giá đỗ", 30)],
     "user_grams": [("Bún", 200), ("Thịt lợn", 110), ("Giá đỗ", 30)],
     "expert": [("Bún", 180), ("Thịt lợn", 100), ("Giá đỗ", 30)],
     "note": "Dữ liệu mẫu: chốt theo khẩu phần một suất bún chả phổ biến."},
    {"key": "com-dau-phu", "user": "user2@nutrismart.vn", "food": "Cơm đậu phụ rau muống",
     "ai": [("Cơm trắng", 150), ("Đậu phụ", 100), ("Rau muống", 100)],
     "user_grams": [("Cơm trắng", 200), ("Đậu phụ", 120), ("Rau muống", 150)],
     "expert": [("Cơm trắng", 200), ("Đậu phụ", 120), ("Rau muống", 150)],
     "note": "Dữ liệu mẫu: đồng ý với số người dùng sửa."},
]


def _user(db, email: str) -> User:
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise SystemExit(f"Chưa có tài khoản {email}. Chạy POST /api/v1/demo/seed trước.")
    return user


def seed_categories(db) -> dict[str, DocCategory]:
    out = {}
    for name, slug in CATEGORIES:
        cat = db.query(DocCategory).filter(DocCategory.slug == slug).first()
        if cat is None:
            cat = DocCategory(name=name, slug=slug)
            db.add(cat)
            db.flush()
            print(f"  + danh mục: {name}")
        else:
            print(f"  = danh mục đã có: {cat.name}")
        out[slug] = cat
    db.commit()
    return out


def seed_articles(db, cats: dict[str, DocCategory], expert: User) -> list[str]:
    created = []
    for url, slug in APPROVED_REAL:
        doc = db.query(Document).filter(Document.source_url == url, Document.deleted_at.is_(None)).first()
        if doc is None:
            try:
                parsed = fetch_and_parse_url(url)
            except Exception as e:  # noqa: BLE001
                print(f"  ! không cào được {url}: {str(e)[:100]}")
                continue
            doc = Document(title=parsed["title"], source_name=parsed["source_name"], source_url=parsed["source_url"],
                           raw_text=parsed["raw_text"], category_id=cats[slug].id, status="APPROVED",
                           uploaded_by=expert.id, approved_by=expert.id, approved_at=datetime.now(timezone.utc))
            db.add(doc)
            db.commit()
            created.append(str(doc.id))
            print(f"  + cào và duyệt: {doc.title}")
        elif doc.status != "APPROVED":
            print(f"  ! đang ở trạng thái {doc.status}, không tự duyệt: {doc.title}")
        elif doc.category_id is None:
            doc.category_id = cats[slug].id
            db.commit()
            print(f"  ~ gắn danh mục {cats[slug].name}: {doc.title}")
        else:
            print(f"  = đã có danh mục: {doc.title}")
    for doc_id in created:
        run_indexing_pipeline(doc_id)   # cắt chunk và tạo vector giống hệt luồng Expert bấm Duyệt
    return created


def seed_pending(db, expert: User) -> None:
    result = crawl_urls(PENDING_URLS, db, uploaded_by_id=expert.id)
    print(f"  cào bài chờ duyệt: thêm {result['inserted']}, đã có {result['skipped']}, lỗi {len(result['errors'])}")
    for err in result["errors"]:
        print(f"    lỗi {err['url']}: {err['error'][:120]}")


def _components(pairs) -> list[dict]:
    return [{"name": name, "grams": grams} for name, grams in pairs]


def seed_corrections(db, expert: User) -> None:
    base = datetime.now(timezone.utc) - timedelta(days=2)
    for index, case in enumerate(CORRECTIONS):
        case_id = uuid.uuid5(SEED_NS, case["key"])
        if db.get(VisionFeedback, case_id) is not None:
            print(f"  = ca sửa đã có: {case['food']}")
            continue
        predicted = portion.build_components(_components(case["ai"]))
        final_items = [{"name": c["name"], "grams": g, "fct_code": c["fct_code"]}
                       for c, (_, g) in zip(predicted, case["user_grams"], strict=True)]
        final = portion.recalculate(final_items, predicted)
        totals_ai = portion.totals(predicted)["energy_kcal"]
        feedback = VisionFeedback(
            id=case_id, user_id=_user(db, case["user"]).id, food_name=case["food"], ai_total_kcal=totals_ai,
            predicted_kcal=totals_ai, predicted_components=predicted, final_components=final,
            final_kcal=portion.totals(final)["energy_kcal"], status="CORRECTED", review_status="PENDING",
            created_at=base + timedelta(hours=index), confirmed_at=base + timedelta(hours=index, minutes=5),
        )
        db.add(feedback)
        db.flush()
        if "expert" in case:
            expert_items = [{"name": c["name"], "grams": g, "fct_code": c["fct_code"]}
                            for c, (_, g) in zip(final, case["expert"], strict=True)]
            few_shot.approve(db, feedback, expert, components=expert_items, note=case["note"])
            print(f"  + ca sửa đã duyệt vào kho few-shot: {case['food']}")
        else:
            print(f"  + ca sửa chờ duyệt: {case['food']}")
        db.commit()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--no-crawl", action="store_true", help="Không cào bài chờ duyệt từ Internet")
    args = parser.parse_args()
    try:
        get_embedding("kiểm tra", timeout=10)
    except (OllamaError, OSError) as e:
        print(f"[CẢNH BÁO] Không tạo được embedding ({type(e).__name__}). Bài viết vẫn được nạp nhưng chunk "
              "không có vector nên RAG chưa truy hồi được. Bật Ollama với bge-m3 rồi chạy lại.")
    with SessionLocal() as db:
        expert = _user(db, EXPERT_EMAIL)
        print("Danh mục:")
        cats = seed_categories(db)
        print("Bài viết đã duyệt:")
        created = seed_articles(db, cats, expert)
        if not args.no_crawl:
            print("Bài chờ duyệt:")
            seed_pending(db, expert)
        print("Ca sửa khẩu phần:")
        seed_corrections(db, expert)
        chunks = db.query(DocChunk).filter(DocChunk.document_id.in_([uuid.UUID(i) for i in created])).count() if created else 0
        print(f"\nXong. Chunk mới tạo: {chunks}. Kho few-shot đang bật: "
              f"{db.query(FewShotExample).filter(FewShotExample.is_active.is_(True)).count()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

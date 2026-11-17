"""Nạp lại data/food_composition_vn2007.csv vào bảng food_composition (upsert, chạy lại an toàn).

Dùng sau khi CSV thay đổi (nhóm duyệt, sửa số liệu). Backend chỉ tự nạp khi bảng còn rỗng.
Chạy từ backend/ (Postgres đang chạy, đã áp migration 29):
    PYTHONUTF8=1 ./.venv/Scripts/python.exe scripts/load_food_composition.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import SessionLocal  # noqa: E402
from app.services import food_composition  # noqa: E402

if __name__ == "__main__":
    db = SessionLocal()
    try:
        print(f"Đã nạp {food_composition.sync_from_csv(db)} dòng vào food_composition")
    finally:
        db.close()

"""NutriSmart Agent - Cloud Database Migration Runner.

Chạy tuần tự toàn bộ các file migration trong `db/migrations/` lên PostgreSQL Cloud
(Supabase, Neon.tech, Render PostgreSQL, AWS RDS,...).

Cách dùng:
    # Cách 1: Dùng DATABASE_URL trong backend/.env
    python scripts/run_migrations.py

    # Cách 2: Truyền trực tiếp connection string qua CLI
    python scripts/run_migrations.py "postgresql+psycopg2://user:pass@host/db?sslmode=require"
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from sqlalchemy import create_engine, text

# Thêm thư mục backend vào sys.path để import config nếu cần
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

try:
    from app.config import settings
    default_db_url = settings.DATABASE_URL
except Exception:
    default_db_url = os.getenv("DATABASE_URL", "")


def find_migrations_dir() -> Path:
    candidates = [
        ROOT_DIR.parent / "db" / "migrations",
        ROOT_DIR / "db" / "migrations",
        Path.cwd() / "db" / "migrations",
        Path.cwd().parent / "db" / "migrations",
    ]
    for p in candidates:
        if p.exists() and p.is_dir():
            return p
    raise FileNotFoundError("Không tìm thấy thư mục `db/migrations/` chứa các file SQL!")


def run_migrations(target_db_url: str | None = None) -> None:
    db_url = target_db_url or default_db_url
    if not db_url:
        print("[LỖI] Không có DATABASE_URL! Hãy cấu hình trong .env hoặc truyền qua tham số dòng lệnh.")
        sys.exit(1)

    # Chuẩn hóa postgres:// thành postgresql://
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    migrations_dir = find_migrations_dir()
    sql_files = sorted(migrations_dir.glob("*.sql"))

    if not sql_files:
        print(f"[CẢNH BÁO] Không có file .sql nào trong {migrations_dir}")
        return

    print("=" * 65)
    print(" NutriSmart Cloud Database Migration")
    print(f" Nguồn migration: {migrations_dir}")
    print(f" Số lượng file : {len(sql_files)}")
    print("=" * 65)

    engine = create_engine(db_url, pool_pre_ping=True)

    with engine.connect() as conn:
        for idx, file_path in enumerate(sql_files, start=1):
            file_name = file_path.name
            print(f"[{idx:02d}/{len(sql_files):02d}] Đang chạy {file_name:<30} ... ", end="", flush=True)
            sql_content = file_path.read_text(encoding="utf-8")
            
            try:
                # Sử dụng text(sql_content) và commit sau mỗi file
                conn.execute(text(sql_content))
                conn.commit()
                print("✓ THÀNH CÔNG")
            except Exception as e:
                # Rollback nếu xảy ra lỗi trong file
                conn.rollback()
                print("✗ THẤT BÀI")
                print(f"\n[LỖI CHI TIẾT] File {file_name}:\n{e}\n")
                sys.exit(1)

    print("\n" + "=" * 65)
    print("✓ Toàn bộ cơ sở dữ liệu đã được khởi tạo và seed dữ liệu thành công!")
    print("=" * 65)


if __name__ == "__main__":
    cli_url = sys.argv[1] if len(sys.argv) > 1 else None
    run_migrations(cli_url)

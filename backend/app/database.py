from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

# Chuẩn hóa URI: Supabase/Neon/Render thường cung cấp URI bắt đầu bằng `postgres://`,
# nhưng SQLAlchemy 2 yêu cầu dialect chuẩn `postgresql://` hoặc `postgresql+psycopg2://`.
_db_url = settings.DATABASE_URL
if _db_url.startswith("postgres://"):
    _db_url = _db_url.replace("postgres://", "postgresql://", 1)

engine = create_engine(_db_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()
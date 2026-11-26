import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.config import settings
from app.routers import auth, catalog, tracking, plans, chat, demo, admin, expert, vision, notifications, articles
from app.services import plan_checkin
from app.services import llm

logger = logging.getLogger(__name__)


def _ensure_auth_schema() -> None:
    """Tự động bổ sung cột token_version và bảng PIN nếu DB deploy chưa chạy migration 33-35."""
    from sqlalchemy import text
    from app.database import engine
    statements = (
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS token_version INT NOT NULL DEFAULT 1",
        """
        CREATE TABLE IF NOT EXISTS email_pins (
            email       VARCHAR(255) PRIMARY KEY,
            pin_hash    VARCHAR(255) NOT NULL,
            attempts    INT NOT NULL DEFAULT 0,
            expires_at  TIMESTAMPTZ NOT NULL,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS pin_send_events (
            id          BIGSERIAL PRIMARY KEY,
            email       VARCHAR(255) NOT NULL,
            ip_address  VARCHAR(64) NOT NULL,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """,
        "CREATE INDEX IF NOT EXISTS ix_pin_send_events_ip_created ON pin_send_events (ip_address, created_at)",
        "CREATE INDEX IF NOT EXISTS ix_pin_send_events_email_created ON pin_send_events (email, created_at)",
    )
    try:
        with engine.begin() as conn:
            for stmt in statements:
                conn.execute(text(stmt))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Không thể tự động kiểm tra schema auth lúc startup: %s", exc)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Bật job nền reconcile check-in và sinh phản hồi AI không đồng bộ."""
    _ensure_auth_schema()
    task = None
    warmup_task = None
    if settings.LLM_PROVIDER == "ollama":
        warmup_task = asyncio.create_task(
            asyncio.to_thread(
                llm.warmup,
                model=settings.OLLAMA_CHAT_MODEL,
                timeout=90.0,
            )
        )
        logger.info("Đã bắt đầu warm-up Ollama model chat ở tác vụ nền")
    if settings.PLAN_CHECKIN_INTERVAL_MINUTES > 0:
        task = asyncio.create_task(plan_checkin.scheduler_loop())
        logger.info("Đã bật job check-in mỗi %s phút",
                    settings.PLAN_CHECKIN_INTERVAL_MINUTES)
    try:
        yield
    finally:
        if task:
            task.cancel()
        if warmup_task and not warmup_task.done():
            warmup_task.cancel()


app = FastAPI(title="NutriSmart Agent API", version="0.1.0", lifespan=lifespan)

# Cấu hình CORS: Cho phép localhost, Vercel (*.vercel.app), Render (*.onrender.com)
# và các domain chỉ định thêm qua biến môi trường CORS_ORIGINS
allowed_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
if settings.CORS_ORIGINS:
    extra = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
    allowed_origins.extend(extra)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$|^https://.*\.vercel\.app$|^https://.*\.onrender\.com$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API = "/api/v1"
app.include_router(auth.router,     prefix=API)
app.include_router(catalog.router,  prefix=API)
app.include_router(tracking.router, prefix=API)
app.include_router(plans.router,    prefix=API)
app.include_router(chat.router,     prefix=API)
app.include_router(demo.router,     prefix=API)
app.include_router(admin.router,    prefix=API)
app.include_router(expert.router,   prefix=API)
app.include_router(vision.router,   prefix=API)
app.include_router(notifications.router, prefix=API)
app.include_router(articles.router, prefix=API)


@app.get("/", include_in_schema=False)
def index():
    return RedirectResponse(url="/docs")


@app.get("/health")
def health():
    return {"status": "ok"}

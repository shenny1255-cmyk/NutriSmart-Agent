import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.config import settings
from app.routers import auth, catalog, tracking, plans, chat, demo, admin, expert, vision, notifications
from app.services import plan_checkin

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Bật job nền reconcile check-in và sinh phản hồi AI không đồng bộ."""
    task = None
    if settings.PLAN_CHECKIN_INTERVAL_MINUTES > 0:
        task = asyncio.create_task(plan_checkin.scheduler_loop())
        logger.info("Đã bật job check-in mỗi %s phút",
                    settings.PLAN_CHECKIN_INTERVAL_MINUTES)
    try:
        yield
    finally:
        if task:
            task.cancel()


app = FastAPI(title="NutriSmart Agent API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=".*",
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


@app.get("/", include_in_schema=False)
def index():
    return RedirectResponse(url="/docs")


@app.get("/health")
def health():
    return {"status": "ok"}

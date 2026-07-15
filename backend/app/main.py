from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from app.routers import auth, catalog, tracking, plans, demo   # thêm demo


from app.routers import auth, catalog, tracking, plans

app = FastAPI(title="NutriSmart Agent API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API = "/api/v1"
app.include_router(auth.router,     prefix=API)
app.include_router(catalog.router,  prefix=API)
app.include_router(tracking.router, prefix=API)
app.include_router(plans.router,    prefix=API)
app.include_router(demo.router, prefix=API)


@app.get("/", include_in_schema=False)
def index():
    return RedirectResponse(url="/docs")


@app.get("/health")
def health():
    return {"status": "ok"}

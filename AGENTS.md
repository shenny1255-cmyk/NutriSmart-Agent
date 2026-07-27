# NutriSmart Agent

Vietnamese-language nutrition & health-coaching app (Nhóm E15). Users register with a
health profile (goal, height/weight, activity level, medical conditions, allergies); the
app computes a daily calorie target and provides an **AI nutrition assistant**, meal
plans, calorie tracking, and admin/expert tooling. **All UI text and code comments are
in Vietnamese.**

## Stack

- **Backend** (`backend/`): FastAPI + SQLAlchemy 2 + Pydantic v2, Python 3.10.
- **DB**: PostgreSQL 16 + pgvector via Docker (`db/docker-compose.yml`). SQL migrations
  in `db/migrations/` run automatically on the first `docker compose up` (fresh volume).
- **Frontend** (`frontend/`): React 19 + Vite + Tailwind + react-router + recharts.
- **AI**: local **Ollama** running `gemma3` — no cloud LLM, nothing leaves the machine.
- **Auth**: JWT (python-jose) + bcrypt (direct, no passlib). Bearer token in `localStorage`.

## Run it (needs 4 things up: Ollama, Postgres, backend, frontend)

```bash
# 0. Ollama running + model pulled:  ollama pull gemma3
# 1. Database
cd db && docker compose up -d            # or restart existing: docker start nutrismart-db nutrismart-redis
# 2. Backend  (venv at backend/.venv and backend/.env already exist locally; both gitignored)
cd backend && ./.venv/Scripts/python.exe -m uvicorn app.main:app --reload   # http://localhost:8000  (docs at /docs)
# 3. Frontend
cd frontend && npm run dev               # http://localhost:5173  (proxies /api -> :8000)
```

Open http://localhost:5173. Demo accounts (via the "Dùng thử ngay (Demo)" button or
`POST /api/v1/demo/seed`): `demo@nutrismart.vn` (admin), `expert1@nutrismart.vn` (expert),
`user1@`/`user2@nutrismart.vn` (user) — all password **`demo1234`**.

## Tests

```bash
cd backend && PYTHONUTF8=1 ./.venv/Scripts/python.exe -m pytest -q
```

- `PYTHONUTF8=1` is **required** on this Windows box or Vietnamese output crashes (cp1252).
- Tests needing Postgres **skip automatically** when the DB is down (see `_db_up()` guards).
- Use **TDD** for backend logic (write the failing test first). Frontend: `npm run build`
  compiles; verify UI by driving the app in a browser.

## Architecture

- Layering: `routers/` (HTTP) → `services/` (`calorie`, `ollama_client`,
  `nutrition_context`, `email`) → `models.py` (SQLAlchemy) → Postgres.
- Config: `pydantic-settings` in `app/config.py`, values from `backend/.env`.
- Frontend API layer: `src/lib/api.js` — `request()` throws `ApiError { status, detail }`
  so pages can show specific messages. Route guards in `App.jsx`: `RequireAuth`,
  `RedirectIfAuthed`.
- `health_profiles.bmi` is a **Postgres generated column** → SQLAlchemy marks it
  `FetchedValue()`; never insert or update it.

## Conventions

- Vietnamese for UI + comments (commit *bodies* in English are fine).
- Match existing style: aligned `=` columns in `models.py`, `# type: ignore` where the
  team added Pyright hints.
- `requirements.txt` is **UTF-16** — append/edit preserving that encoding (e.g. PowerShell
  `Out-File -Encoding Unicode`), don't rewrite it as UTF-8 blindly.

## Gotchas (learned the hard way)

- **Docker Desktop "Inference manager" crash on startup**: turn OFF Settings → **AI →
  Docker Model Runner** and **Gordon**. A corrupt `%LOCALAPPDATA%\Docker\run\dockerInference`
  reparse point can wedge it (undeletable even by `fsutil`); a clean reinstall (4.82) fixed it.
- **Ollama cold start**: first chat after >~5–30 min idle reloads gemma3 (~15–70s, highly
  variable). Client sets `keep_alive=30m` + a 180s timeout; a cold load can surface as a 503.
- **OneDrive + Vite HMR**: the repo lives under a OneDrive-synced path where file-watching
  is flaky — Vite often serves **stale code**. If edits don't show, restart the dev server.
- **bcrypt/passlib**: `security.py` uses `bcrypt` directly (passlib 1.7.4 is broken with
  bcrypt 5.x — `module 'bcrypt' has no attribute '__about__'`).
- **Email verification console link**: `services/email.py` prints the verify link when SMTP
  isn't configured, and attaches its own INFO handler so the link actually appears (Python
  logging otherwise drops INFO).

## Git workflow

- One feature branch per change **off `main`**; integrate via **PR** (this repo merges by PR).
  Never commit directly on `main`.
- **Verify locally before committing** — run the app and/or tests first. Commit only when asked.
- Commits are co-authored to the human maintainer (`ThanhTamK4 <qwertionvnt@gmail.com>`),
  no AI co-signature.

## Feature map (built across recent sessions)

- **AI chat** — `routers/chat.py`, `services/nutrition_context.py`,
  `services/ollama_client.py`, `pages/Chat.jsx`. Grounded Vietnamese assistant; one rolling
  session per user persisted to `chat_sessions`/`chat_messages`.
- **Auth hardening** — `schemas.py` `NormalizedEmail` (any provider, case-insensitive),
  specific error messages via `ApiError`, `PasswordInput` show/hide, `RedirectIfAuthed`.
- **Email verification** — `services/email.py` (real SMTP + console fallback), verify token
  in `security.py`, `/auth/verify` + `/auth/resend-verification`, `pages/Verify.jsx`,
  `components/VerifyBanner.jsx`. Soft enforcement (unverified users can still log in).
  Configure `SMTP_*` in `.env` for real delivery (Gmail needs an App Password).

- **Phân tích món ăn (Vision)** — `routers/vision.py`, `services/gemini_vision.py`, `pages/MealAnalysis.jsx`. Phân tích ảnh đĩa thức ăn bằng Gemini Flash 2.0 (`POST /api/v1/vision/analyze-meal`) và lưu nhật ký bữa ăn (`POST /api/v1/vision/log-meal`).

(`POST /api/v1/plans/generate` **is** real — it prompts gemma3 for a JSON meal plan,
`generated_by="ai-gemma3"`.)

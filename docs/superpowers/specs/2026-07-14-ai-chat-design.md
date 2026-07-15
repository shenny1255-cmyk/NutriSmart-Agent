# Design: AI Chat Assistant (Trợ lý AI)

**Date:** 2026-07-14
**Status:** Approved
**Scope:** Add the missing AI chat feature so the "Trợ lý AI" page works end-to-end,
powered by a local Ollama model and grounded in the user's own health data.

---

## 1. Goal & context

The frontend already has a "Trợ lý AI" nav item and calls `POST /chat/messages`,
but no backend router exists — the page 404s. This design adds that feature.

Key decisions (settled during brainstorming):

- **Engine:** local **Ollama**, model **`gemma3`** (best Vietnamese fluency among the
  user's installed models). Model name and base URL are configurable via env vars.
- **Grounding:** full context — inject the user's health profile, active meal plan,
  and recent (7-day) calorie tracking into the system prompt so replies are personal.
- **History:** one persistent rolling chat session per user, saved to the existing
  `chat_sessions` / `chat_messages` tables; recent turns feed back to the model.
- **HTTP client:** `httpx` calling Ollama's REST API directly (no `ollama` SDK).

The app UI and comments are in Vietnamese; the assistant replies in Vietnamese.

---

## 2. Components

### Backend (FastAPI, `backend/app/`)

| File | Responsibility | Depends on |
|---|---|---|
| `services/ollama_client.py` | `chat(messages: list[dict]) -> str` — POST to Ollama `/api/chat`, return assistant text. Maps connection failure to a clear error. | `httpx`, `config.settings` |
| `services/nutrition_context.py` | `build_system_prompt(db, user) -> str` — pure-ish function assembling profile + active plan + tracking summary into a Vietnamese system prompt. | SQLAlchemy models, `NutritionPlan` |
| `routers/chat.py` | `POST /chat/messages`, `GET /chat/messages`. Orchestrates session, persistence, context, model call. | `deps`, models, both services above |
| `models.py` (edit) | Add `ChatSession` and `ChatMessage` ORM classes mapping the existing tables. | `Base` |
| `schemas.py` (edit) | `ChatIn { message }`, `ChatMessageOut { id, role, content, created_at }`. | pydantic |
| `config.py` (edit) | Add `OLLAMA_BASE_URL="http://localhost:11434"`, `OLLAMA_MODEL="gemma3"`. | pydantic-settings |
| `main.py` (edit) | `app.include_router(chat.router, prefix=API)`. | — |
| `requirements.txt` (edit) | Add `httpx`. | — |

### Frontend (React, `frontend/src/`)

| File | Responsibility |
|---|---|
| `pages/Chat.jsx` (rewrite) | Real chat UI: scrollable message list (user/assistant bubbles), text input, send button, loads history on mount, optimistic user bubble, loading + error states. Currently holds placeholder content (a copy of the Plan page). |
| `lib/api.js` (edit) | Add `chatHistory: () => request('/chat/messages')`. `chat(message)` already exists and is unchanged. |

---

## 3. API contract

### `POST /api/v1/chat/messages`
Auth: Bearer token (existing `get_current_user`).

Request:
```json
{ "message": "Hôm nay tôi nên ăn gì cho bữa tối?" }
```

Response `200`:
```json
{ "reply": "Dựa trên mục tiêu giảm cân của bạn..." }
```

### `GET /api/v1/chat/messages`
Auth: Bearer token. Returns the user's chat history (oldest → newest), excluding
`system` messages:
```json
[
  { "id": 1, "role": "user",      "content": "...", "created_at": "..." },
  { "id": 2, "role": "assistant", "content": "...", "created_at": "..." }
]
```

---

## 4. Data flow (one message)

```
Chat.jsx ──POST /chat/messages {message}──▶ chat router
  1. get_current_user (auth)
  2. find-or-create the user's chat_session (single rolling session)
  3. INSERT user message (role='user')
  4. build_system_prompt(db, user)  →  profile + active plan + 7-day tracking
  5. load last ~10 messages from this session as history
  6. ollama_client.chat([{system}, ...history, {user}])  ──▶ Ollama (gemma3)
  7. INSERT assistant message (role='assistant', flagged=false)
  8. return { reply }
Chat.jsx ◀── append assistant bubble
```

`GET /chat/messages` simply returns steps-3/7 rows for the session.

---

## 5. System prompt shape

`build_system_prompt` produces something like:

```
Bạn là trợ lý dinh dưỡng của ứng dụng NutriSmart. Trả lời bằng tiếng Việt, ngắn gọn,
thực tế. Bạn KHÔNG phải bác sĩ: với mục tiêu y tế (MEDICAL) hoặc bệnh nền nghiêm trọng,
hãy khuyên người dùng tham khảo chuyên gia y tế.

Hồ sơ người dùng:
- Mục tiêu: LOSE_WEIGHT · Mục tiêu calo: 1800 kcal/ngày
- Giới tính: MALE · Tuổi: 28 · Cao 175cm · Nặng 72kg · BMI 23.5
- Bệnh nền: (none) · Dị ứng: đậu phộng

Lộ trình đang áp dụng: phiên bản 2, 1800 kcal/ngày (nếu có).

Theo dõi 7 ngày gần đây: trung bình nạp 1950 kcal, tiêu hao 300 kcal/ngày.
```

Degrade gracefully when data is missing:
- **No health profile** → omit the profile block, add a line nudging the user to
  complete their profile for better advice.
- **No active plan** → omit the plan line.
- **No tracking rows** → omit the tracking line.

The builder must never raise on missing data — missing sections are simply skipped.

---

## 6. Error handling

| Situation | Behavior |
|---|---|
| Ollama not running / connection refused / timeout | Router returns `503` with Vietnamese detail (e.g. "Trợ lý AI tạm thời không phản hồi được"). The user message is **already persisted** (step 3). Frontend shows an error bubble and lets the user retry. |
| Model returns empty text | Treat as `503` with the same friendly message. |
| No health profile | Not an error — system prompt degrades (see §5). |
| History too long | Cap to last ~10 messages before calling the model. |
| Unauthenticated | Existing `get_current_user` raises `401`. |

Ollama call uses a generous timeout (e.g. 120s) since local generation can be slow.

---

## 7. Safety

The system prompt explicitly frames the assistant as a **nutrition aid, not a doctor**,
and instructs it to recommend consulting a professional for `MEDICAL` goals or serious
conditions. This mirrors how `services/calorie.py` already treats `MEDICAL` (no calorie
adjustment — "cần chuyên gia can thiệp"). Assistant messages are stored with
`flagged=false`; the existing `flagged` column remains available for a future
expert-review feature.

---

## 8. Testing

- **Unit — `build_system_prompt`:** pure function; feed a fake `User`/`HealthProfile`
  (and variants with missing profile/plan/tracking) and assert the prompt contains the
  expected lines and omits missing sections without raising. No LLM involved.
- **Router — `POST /chat/messages`:** monkeypatch `ollama_client.chat` to return a
  canned string. Assert: a session is created, both user and assistant rows are
  persisted, and the response `{reply}` matches. No real model call.
- **Router — error path:** monkeypatch `ollama_client.chat` to raise a connection
  error; assert `503` and that the user message was still saved.
- **Manual acceptance:** `ollama serve` running with `gemma3` pulled → start backend →
  send a message from the UI → receive a grounded Vietnamese reply; refresh page →
  history reloads.

---

## 9. Out of scope (YAGNI for today)

- Multiple / named chat sessions (schema supports it; we use one rolling session).
- RAG citations — `message_citations` / `doc_chunks` / pgvector retrieval.
- Streaming (token-by-token) responses — v1 returns the full reply as JSON.
- Expert message-flagging workflow (the `flagged` column stays, unused).

---

## 10. Configuration

New env vars (with safe defaults, so `.env` changes are optional for local dev):

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=gemma3
```

Prerequisite: Ollama installed and running, with `gemma3` pulled
(`ollama pull gemma3`) — already present on the dev machine.

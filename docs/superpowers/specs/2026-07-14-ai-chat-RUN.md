# Trợ lý AI — cách chạy & hoàn tất (tiếp tục sau khi sửa Docker)

Tính năng chat AI đã được viết xong. Phần duy nhất còn lại là chạy full stack
end-to-end, vốn cần Postgres (qua Docker). Docker Desktop hiện chưa chạy được vì
**WSL2 chưa có distro nào được cài**.

## Bước 0 — Sửa WSL2 + Docker (một lần)

Mở **PowerShell với quyền Administrator** rồi chạy:

```powershell
wsl --update
wsl --install --no-distribution   # cài nhân WSL2; Docker Desktop tự dùng distro riêng
```

Nếu được yêu cầu, **khởi động lại máy**. Sau đó mở Docker Desktop và đợi biểu
tượng chuyển sang trạng thái "Engine running".

Kiểm tra:
```powershell
docker info    # không báo lỗi là được
```

## Bước 1 — Khởi động database

```bash
cd db
docker compose up -d      # Postgres (pgvector) + Redis; tự chạy migrations trong db/migrations
```

## Bước 2 — Chạy backend

Môi trường ảo và `.env` đã được tạo sẵn.

```bash
cd backend
./.venv/Scripts/python.exe -m uvicorn app.main:app --reload
```

- Tài liệu API: http://localhost:8000/docs
- Cấu hình Ollama nằm trong `backend/.env` (`OLLAMA_MODEL=gemma3`).
  Đảm bảo Ollama đang chạy: `ollama serve` (hoặc app Ollama đang mở).

## Bước 3 — Chạy frontend

```bash
cd frontend
npm run dev               # http://localhost:5173  (proxy /api -> :8000)
```

Đăng ký một tài khoản ở trang **Đăng ký**, sau đó vào mục **Trợ lý AI** và trò chuyện.

> ⚠️ **Lần nhắn đầu tiên chậm** (~15–60s) vì model gemma3 phải nạp vào RAM.
> Các lần sau nhanh hơn nhiều (~5s). Client đã đặt timeout 180s để chịu được cold start.

## Bước 4 — Chạy 2 test integration còn lại

Khi Postgres đã chạy, hai test router (đang bị skip) sẽ chạy thật:

```bash
cd backend
./.venv/Scripts/python.exe -m pytest -q
# Kỳ vọng: 9 passed (không còn skip)
```

## Bước 5 — Commit

Sau khi xác nhận chat hoạt động end-to-end, commit nhánh `feat/ai-chat`.

---

## Đã hoàn thành & kiểm chứng (không cần Docker)

- `nutrition_context.render_system_prompt` — 6 unit test pass.
- `ollama_client` — test xử lý lỗi kết nối pass; **đã gọi thật gemma3 thành công**,
  trả lời tiếng Việt có căn cứ (tôn trọng dị ứng đậu phộng), ~5.3s khi model đã ấm.
- Frontend `Chat.jsx` build sạch bằng Vite.
- Tổng: `7 passed, 2 skipped` (2 skip chờ Postgres).

## Các tệp đã thêm/sửa

**Backend**
- `app/config.py` — thêm `OLLAMA_BASE_URL`, `OLLAMA_MODEL`
- `app/models.py` — thêm `ChatSession`, `ChatMessage`
- `app/schemas.py` — thêm `ChatIn`, `ChatMessageOut`, `ChatReplyOut`
- `app/services/ollama_client.py` — mới
- `app/services/nutrition_context.py` — mới
- `app/routers/chat.py` — mới
- `app/main.py` — đăng ký chat router
- `requirements.txt` — thêm `httpx`
- `.env` — mới (local, đã gitignore)
- `conftest.py`, `tests/` — mới

**Frontend**
- `src/pages/Chat.jsx` — viết lại thành giao diện chat thật
- `src/lib/api.js` — thêm `chatHistory()`

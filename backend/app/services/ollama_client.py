"""Client gọi Ollama (LLM chạy local) qua REST API.

Ollama mặc định lắng nghe ở http://localhost:11434 và cung cấp endpoint
POST /api/chat nhận {model, messages, stream}. Ta dùng stream=False để lấy
trọn câu trả lời trong một response JSON.
"""

import httpx

from app.config import settings


class OllamaError(Exception):
    """Không gọi được model (server tắt, timeout, hoặc trả về rỗng)."""


def chat(
    messages: list[dict],
    *,
    model: str | None = None,
    base_url: str | None = None,
    timeout: float = 180.0,   # rộng rãi cho lần gọi đầu (model phải nạp vào RAM)
) -> str:
    """Gửi danh sách messages tới Ollama, trả về nội dung câu trả lời (text).

    messages: [{"role": "system"|"user"|"assistant", "content": "..."}]
    """
    model = model or settings.OLLAMA_MODEL
    base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")

    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "keep_alive": settings.OLLAMA_KEEP_ALIVE,
    }

    try:
        resp = httpx.post(f"{base_url}/api/chat", json=payload, timeout=timeout)
        resp.raise_for_status()
    except httpx.HTTPError as e:
        raise OllamaError(f"Không gọi được Ollama: {e}") from e

    content = (resp.json().get("message") or {}).get("content", "").strip()
    if not content:
        raise OllamaError("Ollama trả về câu trả lời rỗng")
    return content

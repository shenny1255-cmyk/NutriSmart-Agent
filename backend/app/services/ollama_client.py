"""Client gọi Ollama (LLM chạy local) qua REST API.

Ollama mặc định lắng nghe ở http://localhost:11434 và cung cấp endpoint
POST /api/chat nhận {model, messages, stream}. Ta dùng stream=False để lấy
trọn câu trả lời trong một response JSON.
"""

import httpx
import logging

from app.config import settings

log = logging.getLogger("nutrismart.ollama")


class OllamaError(Exception):
    """Không gọi được model (server tắt, timeout, hoặc trả về rỗng)."""


def warmup(*, model: str | None = None, timeout: float = 90.0) -> None:
    """Nạp model vào RAM trước request đầu tiên; lỗi không chặn ứng dụng khởi động."""
    try:
        chat(
            [{"role": "user", "content": "Trả lời đúng một từ: sẵn sàng."}],
            model=model or settings.OLLAMA_CHAT_MODEL,
            timeout=timeout,
            options={"num_predict": 1, "temperature": 0},
        )
        log.info("Đã warm-up Ollama model %s", model or settings.OLLAMA_CHAT_MODEL)
    except Exception as e:  # noqa: BLE001 — warm-up tùy chọn không được làm hỏng startup
        log.warning("Không warm-up được Ollama model: %s", e)


def chat(
    messages: list[dict],
    *,
    model: str | None = None,
    base_url: str | None = None,
    timeout: float = 180.0,   # rộng rãi cho lần gọi đầu (model phải nạp vào RAM)
    options: dict | None = None,
) -> str:
    """Gửi danh sách messages tới Ollama, trả về nội dung câu trả lời (text).

    messages: [{"role": "system"|"user"|"assistant", "content": "..."}]
    options:  ghi đè tham số sinh của Ollama (vd num_predict lớn hơn cho JSON dài).
    """
    model = model or settings.OLLAMA_MODEL
    base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")

    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "keep_alive": settings.OLLAMA_KEEP_ALIVE,
        "options": {
            "num_ctx": 2048,
            "num_predict": 250,
            "temperature": 0.6,
            **(options or {}),
        },
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


def chat_stream(
    messages: list[dict],
    *,
    model: str | None = None,
    base_url: str | None = None,
    timeout: float = 180.0,
):
    """Stream từng token từ Ollama /api/chat với stream=True."""
    import json
    model = model or settings.OLLAMA_MODEL
    base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")

    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
        "keep_alive": settings.OLLAMA_KEEP_ALIVE,
        "options": {
            "num_ctx": 2048,
            "num_predict": 250,
            "temperature": 0.6,
        },
    }

    try:
        with httpx.stream("POST", f"{base_url}/api/chat", json=payload, timeout=timeout) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    chunk = (data.get("message") or {}).get("content", "")
                    if chunk:
                        yield chunk
                except Exception:
                    continue
    except httpx.HTTPError as e:
        raise OllamaError(f"Không gọi được Ollama Stream: {e}") from e


def get_embedding(
    prompt: str,
    *,
    model: str | None = None,
    base_url: str | None = None,
    timeout: float = 60.0,
) -> list[float]:
    """Gửi đoạn văn bản tới Ollama endpoint /api/embeddings, trả về danh sách vector float."""
    model = model or getattr(settings, "OLLAMA_EMBEDDING_MODEL", "bge-m3")
    base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")

    payload = {
        "model": model,
        "prompt": prompt,
    }

    try:
        resp = httpx.post(f"{base_url}/api/embeddings", json=payload, timeout=timeout)
        resp.raise_for_status()
    except httpx.HTTPError as e:
        raise OllamaError(f"Không gọi được Ollama Embeddings: {e}") from e

    embedding = resp.json().get("embedding")
    if not embedding or not isinstance(embedding, list):
        raise OllamaError("Ollama Embeddings trả về kết quả rỗng hoặc không đúng định dạng")
    return embedding

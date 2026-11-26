"""AI Provider Adapter - một giao diện chung cho mọi lời gọi LLM (kế hoạch ĐATN v2, mục 2.2 + 3).

Chọn nhà cung cấp qua `.env`:
- LLM_PROVIDER=ollama (mặc định): Ollama tự host - dữ liệu không rời máy chủ.
- LLM_PROVIDER=gemini: Google Gemini - khách hàng không cần cài Ollama.

Khi gọi cloud, adapter tự:
1. Ẩn danh hóa messages (services/privacy.py): bỏ họ tên, email, số điện thoại; tuổi → khoảng.
2. Ghi audit log mỗi lần dữ liệu được gửi ra ngoài (nhà cung cấp, mục đích, số ký tự,
   loại dữ liệu đã xóa, độ trễ, số token) - phục vụ cả quyền riêng tư lẫn bảng chi phí.
3. Rơi về Ollama khi cloud lỗi/hết quota (LLM_FALLBACK_LOCAL=true).

Người dùng bật "chỉ xử lý bằng AI nội bộ" (user_profile.ai_local_only) → luôn dùng Ollama.

Embedding (bge-m3) KHÔNG đi qua adapter: đổi model embedding phải index lại toàn bộ doc_chunks.
"""
from __future__ import annotations

import logging
import os
import time
from collections.abc import Iterator

from app.config import settings
from app.services import ollama_client, privacy
from app.services.llm_errors import LLMError

log = logging.getLogger("nutrismart.llm")

__all__ = ["LLMError", "chat", "chat_stream", "warmup", "resolve_provider", "to_gemini_contents"]

# Thử lần lượt nếu model trước lỗi/ngừng phục vụ/quá tải. Dùng CHUNG danh sách với Vision để chỉ
# phải cập nhật một chỗ khi Google ngừng một model (gemini-2.5-flash-lite đã ngừng cho người dùng mới).
from app.services.gemini_vision import GEMINI_VISION_MODELS as GEMINI_FALLBACK_MODELS  # noqa: E402


# ---------- Chọn nhà cung cấp ----------

def resolve_provider(user=None) -> str:
    provider = (settings.LLM_PROVIDER or "ollama").strip().lower()
    profile = getattr(user, "profile", None)
    if provider != "ollama" and getattr(profile, "ai_local_only", False):
        return "ollama"
    return provider


def _full_name(user) -> str | None:
    profile = getattr(user, "profile", None)
    return getattr(profile, "full_name", None)


# ---------- Ollama ----------

def _ollama_chat(messages: list[dict], *, model=None, timeout=180.0, max_tokens=None,
                 temperature=None, json_schema=None, ollama_options=None) -> str:
    options = dict(ollama_options or {})
    if max_tokens is not None:
        options["num_predict"] = max_tokens
    if temperature is not None:
        options["temperature"] = temperature
    kwargs = {"timeout": timeout, "options": options or None}
    if model:
        kwargs["model"] = model
    if json_schema is not None:
        kwargs["response_format"] = json_schema
    # Gọi qua module (không import thẳng hàm) để test monkeypatch được ollama_client.chat
    return ollama_client.chat(messages, **kwargs)


def _ollama_stream(messages: list[dict], *, model=None, timeout=180.0) -> Iterator[str]:
    kwargs = {"timeout": timeout}
    if model:
        kwargs["model"] = model
    yield from ollama_client.chat_stream(messages, **kwargs)


# ---------- Gemini ----------

def to_gemini_contents(messages: list[dict]) -> tuple[str | None, list[dict]]:
    """messages kiểu OpenAI/Ollama → (system_instruction, contents của Gemini).

    Gemini nhận system prompt riêng; vai "assistant" gọi là "model".
    """
    system_parts, contents = [], []
    for m in messages:
        role, text = m.get("role"), str(m.get("content") or "")
        if role == "system":
            system_parts.append(text)
        else:
            contents.append({"role": "model" if role == "assistant" else "user",
                             "parts": [{"text": text}]})
    return ("\n\n".join(system_parts) or None), contents


def _gemini_models() -> list[str]:
    first = (settings.GEMINI_CHAT_MODEL or "").strip()
    return [first] + [m for m in GEMINI_FALLBACK_MODELS if m != first] if first else list(GEMINI_FALLBACK_MODELS)


def _gemini_client(timeout: float):
    from google import genai
    from google.genai import types
    key = settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY")
    if not key:
        raise LLMError("GEMINI_API_KEY chưa được cấu hình")
    return genai.Client(api_key=key, http_options=types.HttpOptions(timeout=int(timeout * 1000)))


def _gemini_config(system, max_tokens, temperature, json_schema, thinking_off: bool):
    from google.genai import types
    kw: dict = {"max_output_tokens": max_tokens or settings.LLM_MAX_OUTPUT_TOKENS}
    if system:
        kw["system_instruction"] = system
    if temperature is not None:
        kw["temperature"] = temperature
    if json_schema is not None:
        kw["response_mime_type"] = "application/json"
        kw["response_json_schema"] = json_schema
    if thinking_off:
        # Tắt "thinking" để token không bị suy luận ăn mất và độ trễ thấp (câu trả lời tư vấn ngắn).
        kw["thinking_config"] = types.ThinkingConfig(thinking_budget=0)
    return types.GenerateContentConfig(**kw)


def _supports_thinking_budget(model: str) -> bool:
    """thinking_budget=0 chỉ hợp lệ với dòng 2.5; dòng 3.x trả 400 INVALID_ARGUMENT."""
    return model.startswith("gemini-2.5")


def _usage(resp, model: str) -> dict:
    um = getattr(resp, "usage_metadata", None)
    return {"model": model,
            "prompt_tokens": getattr(um, "prompt_token_count", None),
            "output_tokens": getattr(um, "candidates_token_count", None)}


def _gemini_chat(messages: list[dict], *, timeout=180.0, max_tokens=None, temperature=None,
                 json_schema=None) -> tuple[str, dict]:
    client = _gemini_client(timeout)
    system, contents = to_gemini_contents(messages)
    last: Exception | None = None
    for model in _gemini_models():
        try:
            resp = client.models.generate_content(
                model=model, contents=contents,
                config=_gemini_config(system, max_tokens, temperature, json_schema,
                                      thinking_off=_supports_thinking_budget(model)))
            text = (resp.text or "").strip()
            if not text:
                raise LLMError(f"{model} trả về câu trả lời rỗng")
            return text, _usage(resp, model)
        except Exception as e:  # noqa: BLE001 - thử model kế tiếp (ngừng phục vụ, quá tải, quota)
            last = e
            log.warning("Gemini %s lỗi: %s", model, e)
    raise LLMError(f"Không gọi được Gemini: {last}")


def _gemini_stream(messages: list[dict], *, timeout=180.0, max_tokens=None,
                   meta: dict | None = None) -> Iterator[str]:
    """`meta` (nếu có) nhận tên model thực sự trả lời - model dự phòng có thể khác model đầu danh sách."""
    client = _gemini_client(timeout)
    system, contents = to_gemini_contents(messages)
    last: Exception | None = None
    for model in _gemini_models():
        produced = False
        try:
            for chunk in client.models.generate_content_stream(
                    model=model, contents=contents,
                    config=_gemini_config(system, max_tokens, None, None,
                                          thinking_off=_supports_thinking_budget(model))):
                if chunk.text:
                    if not produced and meta is not None:
                        meta["model"] = model
                    produced = True
                    yield chunk.text
            if produced:
                return
            raise LLMError(f"{model} stream rỗng")
        except Exception as e:  # noqa: BLE001
            if produced:          # đã gửi một phần cho người dùng → không đổi model giữa chừng
                raise LLMError(f"Gemini stream đứt giữa chừng: {e}") from e
            last = e
            log.warning("Gemini stream %s lỗi: %s", model, e)
    raise LLMError(f"Không gọi được Gemini stream: {last}")


# ---------- Ghi vết gửi dữ liệu ra ngoài ----------

def _audit_external_call(*, actor_id, provider: str, model: str | None, purpose: str,
                         chars_sent: int, redactions: dict, latency_ms: int, ok: bool,
                         usage: dict | None = None, error: str | None = None,
                         extra: dict | None = None) -> None:
    """Ghi audit_logs bằng session riêng - lỗi ghi vết không được làm hỏng câu trả lời."""
    try:
        from app.database import SessionLocal
        from app.services.audit import write_audit
        with SessionLocal() as db:
            write_audit(db, actor_id, "AI_EXTERNAL_CALL", "llm", None, after={
                "provider": provider, "model": model, "purpose": purpose,
                "chars_sent": chars_sent, "redactions": redactions,
                "latency_ms": latency_ms, "ok": ok, "usage": usage, "error": error,
                **(extra or {}),
            })
            db.commit()
    except Exception as e:  # noqa: BLE001
        log.warning("Không ghi được audit lời gọi AI bên ngoài: %s", e)


def _audit_kwargs(user, purpose, safe_messages, report, t0) -> dict:
    return {
        "actor_id": getattr(user, "id", None), "provider": "gemini", "purpose": purpose,
        "chars_sent": sum(len(str(m.get("content") or "")) for m in safe_messages),
        "redactions": report, "latency_ms": int((time.perf_counter() - t0) * 1000),
    }


# ---------- API công khai ----------

def chat(messages: list[dict], *, user=None, purpose: str = "chat", ollama_model: str | None = None,
         timeout: float = 180.0, max_tokens: int | None = None, temperature: float | None = None,
         json_schema: dict | None = None, ollama_options: dict | None = None) -> str:
    """Trả về toàn bộ câu trả lời. Ném LLMError nếu mọi nhà cung cấp đều thất bại."""
    provider = resolve_provider(user)
    local = dict(model=ollama_model, timeout=timeout, max_tokens=max_tokens, temperature=temperature,
                 json_schema=json_schema, ollama_options=ollama_options)
    if provider == "ollama":
        return _ollama_chat(messages, **local)
    if provider != "gemini":
        raise LLMError(f"LLM_PROVIDER không được hỗ trợ: {provider}")

    safe, report = privacy.anonymize_messages(messages, full_name=_full_name(user))
    t0 = time.perf_counter()
    try:
        text, usage = _gemini_chat(safe, timeout=timeout, max_tokens=max_tokens,
                                   temperature=temperature, json_schema=json_schema)
    except Exception as e:  # noqa: BLE001
        _audit_external_call(**_audit_kwargs(user, purpose, safe, report, t0),
                             model=None, ok=False, error=str(e)[:300])
        if settings.LLM_FALLBACK_LOCAL:
            log.warning("Cloud LLM lỗi (%s) - chuyển sang Ollama nội bộ", e)
            return _ollama_chat(messages, **local)   # chạy nội bộ: không cần ẩn danh
        raise e if isinstance(e, LLMError) else LLMError(str(e))
    usage = dict(usage or {})
    model = usage.pop("model", None)
    _audit_external_call(**_audit_kwargs(user, purpose, safe, report, t0),
                         model=model, ok=True, usage=usage)
    return text


def chat_stream(messages: list[dict], *, user=None, purpose: str = "chat",
                ollama_model: str | None = None, timeout: float = 180.0) -> Iterator[str]:
    """Stream từng đoạn câu trả lời. Fallback sang Ollama chỉ khi chưa gửi token nào."""
    provider = resolve_provider(user)
    if provider == "ollama":
        yield from _ollama_stream(messages, model=ollama_model, timeout=timeout)
        return
    if provider != "gemini":
        raise LLMError(f"LLM_PROVIDER không được hỗ trợ: {provider}")

    safe, report = privacy.anonymize_messages(messages, full_name=_full_name(user))
    t0 = time.perf_counter()
    produced = False
    meta: dict = {}
    try:
        for tok in _gemini_stream(safe, timeout=timeout, meta=meta):
            produced = True
            yield tok
    except Exception as e:  # noqa: BLE001
        _audit_external_call(**_audit_kwargs(user, purpose, safe, report, t0),
                             model=None, ok=False, error=str(e)[:300])
        if not produced and settings.LLM_FALLBACK_LOCAL:
            log.warning("Cloud LLM stream lỗi (%s) - chuyển sang Ollama nội bộ", e)
            yield from _ollama_stream(messages, model=ollama_model, timeout=timeout)
            return
        raise e if isinstance(e, LLMError) else LLMError(str(e))
    # Stream của Gemini không trả usage_metadata ổn định theo từng chunk → chỉ ghi model thực tế
    _audit_external_call(**_audit_kwargs(user, purpose, safe, report, t0),
                         model=meta.get("model"), ok=True)


def warmup(*, model: str | None = None, timeout: float = 90.0) -> None:
    """Chỉ cần nạp sẵn model khi chạy Ollama; cloud không có khái niệm cold start cục bộ."""
    if resolve_provider() == "ollama":
        ollama_client.warmup(model=model, timeout=timeout)

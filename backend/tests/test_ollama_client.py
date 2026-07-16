"""Tests cho ollama_client — phần xử lý lỗi kết nối (không cần model chạy)."""

import pytest

from app.services.ollama_client import chat, OllamaError


def test_unreachable_server_raises_ollama_error():
    # Cổng đóng → phải raise OllamaError chứ không phải lỗi httpx thô
    with pytest.raises(OllamaError):
        chat(
            [{"role": "user", "content": "xin chào"}],
            base_url="http://localhost:59999",   # không có server ở đây
            timeout=2.0,
        )

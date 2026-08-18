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


def test_chat_gui_json_schema_cho_ollama(monkeypatch):
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"message": {"content": '{"days": []}'}}

    def fake_post(url, *, json, timeout):
        captured.update({"url": url, "payload": json, "timeout": timeout})
        return FakeResponse()

    schema = {
        "type": "object",
        "properties": {"days": {"type": "array"}},
        "required": ["days"],
    }
    monkeypatch.setattr("app.services.ollama_client.httpx.post", fake_post)

    result = chat(
        [{"role": "user", "content": "Tạo lộ trình"}],
        base_url="http://ollama.test",
        response_format=schema,
        options={"temperature": 0},
    )

    assert result == '{"days": []}'
    assert captured["payload"]["format"] == schema
    assert captured["payload"]["options"]["temperature"] == 0

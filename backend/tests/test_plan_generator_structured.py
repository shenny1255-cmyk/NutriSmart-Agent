import json

from app.services import plan_generator


def _valid_plan_json() -> str:
    return json.dumps({
        "days": [
            {
                "meals": [
                    {"type": "Sáng", "name": f"Bữa sáng {day}", "kcal": 500},
                    {"type": "Trưa", "name": f"Bữa trưa {day}", "kcal": 700},
                    {"type": "Tối", "name": f"Bữa tối {day}", "kcal": 600},
                ],
                "exercise": f"Đi bộ ngày {day} trong 30 phút",
            }
            for day in range(1, 8)
        ]
    }, ensure_ascii=False)


def test_llm_days_ep_json_schema_va_nhiet_do_thap(monkeypatch):
    captured = {}

    def fake_chat(messages, **kwargs):
        captured["messages"] = messages
        captured["kwargs"] = kwargs
        return _valid_plan_json()

    monkeypatch.setattr(plan_generator.ollama_client, "chat", fake_chat)

    days = plan_generator._llm_days("prompt kiểm thử")

    assert len(days) == 7
    assert captured["kwargs"]["options"]["temperature"] == 0
    schema = captured["kwargs"]["response_format"]
    assert schema["type"] == "object"
    assert schema["properties"]["days"]["minItems"] == 7
    assert schema["properties"]["days"]["maxItems"] == 7


def test_llm_days_thu_lai_mot_lan_khi_cau_truc_khong_hop_le(monkeypatch):
    replies = iter(['{"days": []}', _valid_plan_json()])
    calls = []

    def fake_chat(messages, **kwargs):
        calls.append(messages)
        return next(replies)

    monkeypatch.setattr(plan_generator.ollama_client, "chat", fake_chat)

    days = plan_generator._llm_days("prompt kiểm thử")

    assert len(days) == 7
    assert len(calls) == 2
    assert "không đúng cấu trúc" in calls[1][-1]["content"]


def test_llm_days_dung_fallback_sau_hai_ket_qua_khong_hop_le(monkeypatch):
    calls = []

    def fake_chat(messages, **kwargs):
        calls.append(messages)
        return '{"days": [{"meals": [], "exercise": ""}]}'

    monkeypatch.setattr(plan_generator.ollama_client, "chat", fake_chat)

    assert plan_generator._llm_days("prompt kiểm thử") is None
    assert len(calls) == 2

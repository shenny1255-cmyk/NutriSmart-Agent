"""Test AI Provider Adapter (kế hoạch ĐATN v2, mục 2.2 + 3).

Không gọi model thật: các hàm gọi Ollama/Gemini được monkeypatch.
"""
from types import SimpleNamespace

import pytest

from app.config import settings
from app.services import llm


def _user(local_only=False, name="Nguyễn Văn An"):
    return SimpleNamespace(id="u-1", email="an@example.com",
                           profile=SimpleNamespace(full_name=name, ai_local_only=local_only))


@pytest.fixture
def calls(monkeypatch):
    """Ghi lại lời gọi tới từng provider + audit, không gọi mạng."""
    rec = {"ollama": [], "gemini": [], "audit": []}

    def fake_ollama(messages, **kw):
        rec["ollama"].append((messages, kw))
        return "trả lời từ ollama"

    def fake_gemini(messages, **kw):
        rec["gemini"].append((messages, kw))
        return "trả lời từ gemini", {"prompt_tokens": 12, "output_tokens": 5}

    monkeypatch.setattr(llm, "_ollama_chat", fake_ollama)
    monkeypatch.setattr(llm, "_gemini_chat", fake_gemini)
    monkeypatch.setattr(llm, "_audit_external_call", lambda **kw: rec["audit"].append(kw))
    return rec


def test_mac_dinh_van_la_ollama_khong_doi_hanh_vi():
    from app.config import Settings
    assert Settings.model_fields["LLM_PROVIDER"].default == "ollama"
    assert Settings.model_fields["LLM_FALLBACK_LOCAL"].default is True


def test_che_do_ollama_khong_an_danh_khong_audit(monkeypatch, calls):
    monkeypatch.setattr(settings, "LLM_PROVIDER", "ollama")
    out = llm.chat([{"role": "user", "content": "Tôi là Nguyễn Văn An"}], user=_user(), purpose="chat")
    assert out == "trả lời từ ollama"
    # Chạy nội bộ: dữ liệu không rời máy → giữ nguyên, không cần audit gửi ngoài
    assert calls["ollama"][0][0][0]["content"] == "Tôi là Nguyễn Văn An"
    assert calls["audit"] == []


def test_che_do_gemini_an_danh_va_ghi_audit(monkeypatch, calls):
    monkeypatch.setattr(settings, "LLM_PROVIDER", "gemini")
    msgs = [{"role": "system", "content": "Bạn đang trò chuyện với Nguyễn Văn An. Tuổi: 27"},
            {"role": "user", "content": "email an@example.com"}]
    out = llm.chat(msgs, user=_user(), purpose="chat")
    assert out == "trả lời từ gemini"
    sent = " ".join(m["content"] for m in calls["gemini"][0][0])
    assert "Nguyễn Văn An" not in sent and "an@example.com" not in sent and "Tuổi: 27" not in sent
    assert len(calls["audit"]) == 1
    a = calls["audit"][0]
    assert a["provider"] == "gemini" and a["purpose"] == "chat" and a["actor_id"] == "u-1"
    assert a["redactions"]["name"] >= 1 and a["redactions"]["email"] == 1
    assert a["usage"] == {"prompt_tokens": 12, "output_tokens": 5}
    assert a["ok"] is True and a["latency_ms"] >= 0


def test_nguoi_dung_chon_chi_ai_noi_bo_luon_di_ollama(monkeypatch, calls):
    monkeypatch.setattr(settings, "LLM_PROVIDER", "gemini")
    llm.chat([{"role": "user", "content": "hi"}], user=_user(local_only=True))
    assert len(calls["ollama"]) == 1 and calls["gemini"] == []


def test_gemini_loi_thi_roi_ve_ollama(monkeypatch, calls):
    monkeypatch.setattr(settings, "LLM_PROVIDER", "gemini")
    monkeypatch.setattr(settings, "LLM_FALLBACK_LOCAL", True)

    def boom(messages, **kw):
        raise llm.LLMError("hết quota")
    monkeypatch.setattr(llm, "_gemini_chat", boom)

    assert llm.chat([{"role": "user", "content": "hi"}], user=_user()) == "trả lời từ ollama"
    assert calls["audit"][0]["ok"] is False          # lần gọi cloud thất bại vẫn được ghi vết


def test_tat_fallback_thi_bao_loi(monkeypatch, calls):
    monkeypatch.setattr(settings, "LLM_PROVIDER", "gemini")
    monkeypatch.setattr(settings, "LLM_FALLBACK_LOCAL", False)
    monkeypatch.setattr(llm, "_gemini_chat", lambda m, **kw: (_ for _ in ()).throw(llm.LLMError("x")))
    with pytest.raises(llm.LLMError):
        llm.chat([{"role": "user", "content": "hi"}], user=_user())


def test_loi_ollama_cung_la_llm_error():
    # Router bắt một loại lỗi chung cho mọi provider
    from app.services.ollama_client import OllamaError
    assert issubclass(OllamaError, llm.LLMError)


def test_chuyen_doi_messages_sang_dinh_dang_gemini():
    system, contents = llm.to_gemini_contents([
        {"role": "system", "content": "Bạn là trợ lý."},
        {"role": "user", "content": "Chào"},
        {"role": "assistant", "content": "Xin chào!"},
        {"role": "user", "content": "Tư vấn giúp tôi"},
    ])
    assert system == "Bạn là trợ lý."
    assert [c["role"] for c in contents] == ["user", "model", "user"]
    assert contents[1]["parts"][0]["text"] == "Xin chào!"


def test_stream_gemini_cung_an_danh_va_audit(monkeypatch, calls):
    monkeypatch.setattr(settings, "LLM_PROVIDER", "gemini")
    seen = {}

    def fake_stream(messages, **kw):
        seen["messages"] = messages
        yield "Xin "
        yield "chào"
    monkeypatch.setattr(llm, "_gemini_stream", fake_stream)

    tokens = list(llm.chat_stream([{"role": "user", "content": "Tôi là Nguyễn Văn An"}], user=_user()))
    assert "".join(tokens) == "Xin chào"
    assert "Nguyễn Văn An" not in seen["messages"][0]["content"]
    assert calls["audit"][0]["provider"] == "gemini" and calls["audit"][0]["ok"] is True


# ---------- Job nền phải tôn trọng lựa chọn "chỉ AI nội bộ" của người dùng ----------

def test_feedback_checkin_truyen_nguoi_dung_cho_adapter(monkeypatch):
    from app.services import plan_checkin
    captured = {}

    def fake_chat(messages, **kw):
        captured.update(kw)
        return "Nhận xét"
    monkeypatch.setattr(plan_checkin.llm, "chat", fake_chat)
    checkin = SimpleNamespace(id=1, period_number=1, goal_snapshot="LOSE_WEIGHT", target_kcal_snapshot=1800,
                              weight_change_kg=-0.4, adherence_pct=80, energy_level=3, hunger_level=3,
                              sleep_quality=3, recommendation="CONTINUE_AND_TRACK", recommendation_reason="Tốt")
    u = _user(local_only=True)
    assert plan_checkin.generate_feedback(checkin, user=u) == ("Nhận xét", "COMPLETED")
    assert captured["user"] is u and captured["purpose"] == "checkin_feedback"


def test_nhan_xet_danh_gia_lo_trinh_truyen_nguoi_dung(monkeypatch):
    from app.services import plan_evaluator
    captured = {}
    monkeypatch.setattr(plan_evaluator.llm, "chat", lambda m, **kw: captured.update(kw) or "Ổn")
    u = _user()
    plan_evaluator._llm_feedback({"goal": "MAINTAIN"}, "ACHIEVED", 2000, 1950.0, -0.2, user=u)
    assert captured["user"] is u and captured["purpose"] == "plan_evaluate"


def test_warmup_nhan_tham_so_nhu_luc_khoi_dong_app(monkeypatch):
    # main.py gọi llm.warmup(model=..., timeout=...) - sai chữ ký làm backend sập khi khởi động
    seen = {}
    monkeypatch.setattr(llm.ollama_client, "warmup", lambda **kw: seen.update(kw))
    monkeypatch.setattr(settings, "LLM_PROVIDER", "ollama")
    llm.warmup(model="gemma3:1b", timeout=90.0)
    assert seen == {"model": "gemma3:1b", "timeout": 90.0}

    seen.clear()
    monkeypatch.setattr(settings, "LLM_PROVIDER", "gemini")
    llm.warmup(model="gemma3:1b", timeout=90.0)
    assert seen == {}          # cloud: không nạp model cục bộ

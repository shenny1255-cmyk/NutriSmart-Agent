"""Tests cho ràng buộc quốc gia trong RAG & Cảnh báo Thuốc Cấm/Hạn chế."""

import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.main import app
from app.database import engine, SessionLocal
from app.models import User, HealthProfile, Drug
from app.services.nutrition_context import (
    render_system_prompt, get_country_drug_rules, gather_context, build_system_prompt
)
import app.routers.chat as chat_router
from app.services import ollama_client


def _db_up() -> bool:
    try:
        with engine.connect() as c:
            c.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


requires_db = pytest.mark.skipif(not _db_up(), reason="Postgres chưa chạy")

client = TestClient(app)


def test_render_system_prompt_with_country_drug_rules():
    """Kiểm tra render_system_prompt khi có danh mục thuốc cấm/hạn chế."""
    ctx = {
        "full_name": "Nguyễn Văn A",
        "country_code": "VN",
        "country_name": "Việt Nam",
        "drug_rules": [
            {
                "drug_name": "Sibutramine",
                "active_ingredient": "Sibutramine",
                "status": "BANNED",
                "note": "Bị cấm do nguy cơ tim mạch",
            },
            {
                "drug_name": "Pseudoephedrine",
                "active_ingredient": "Pseudoephedrine",
                "status": "RESTRICTED",
                "note": "Thuốc kê đơn",
            },
        ],
        "profile": None,
        "active_plan": None,
        "tracking": None,
    }
    prompt = render_system_prompt(ctx)

    assert "Việt Nam (VN)" in prompt
    assert "Sibutramine" in prompt
    assert "CẤM (BANNED)" in prompt
    assert "Bị cấm do nguy cơ tim mạch" in prompt
    assert "Pseudoephedrine" in prompt
    assert "RESTRICTED" in prompt
    assert "DANH MỤC QUY ĐỊNH DƯỢC PHẨM" in prompt


@requires_db
def test_get_country_drug_rules_from_db():
    """Kiểm tra get_country_drug_rules lấy đúng thuốc CẤM/HẠN CHẾ từ DB."""
    db = SessionLocal()
    try:
        # Nạp thuốc chuẩn nếu DB chưa có
        from app.routers.admin import _ensure_default_drugs
        _ensure_default_drugs(db)

        cname, rules = get_country_drug_rules(db, "VN")
        assert cname in ["Việt Nam", "VN"]
        assert len(rules) > 0
    finally:
        db.close()


@requires_db
def test_gather_context_includes_country_rules():
    """Kiểm tra gather_context nạp country_code và drug_rules của user."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.country_code == "VN").first()
        if not user:
            user = User(
                email=f"test_rag_{uuid.uuid4().hex[:6]}@example.com",
                password_hash="hash",
                full_name="User RAG Test",
                country_code="VN",
            )
            db.add(user)
            db.commit()

        ctx = gather_context(db, user)
        assert ctx["country_code"] == "VN"
        assert "drug_rules" in ctx
    finally:
        db.close()


@requires_db
def test_chat_system_prompt_receives_banned_drug_warning(monkeypatch):
    """Kiểm tra khi gửi chat hỏi thuốc cấm ở VN, System Prompt gửi cho LLM chứa cảnh báo thuốc cấm."""
    cc = "VN"

    # Đăng ký user test với quốc gia VN
    test_email = f"banned_drug_{uuid.uuid4().hex[:10]}@example.com"
    r = client.post("/api/v1/auth/register", json={
        "email": test_email,
        "password": "password123", "full_name": "Test Thuốc Cấm", "country_code": cc,
        "profile": {"gender": "MALE", "birth_date": "1996-01-01", "height_cm": 175,
                    "weight_kg": 72, "activity_level": 3, "goal": "MAINTAIN",
                    "condition_ids": [], "allergen_ids": []},
    })
    assert r.status_code == 201, r.text
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    db = SessionLocal()
    try:
        from app.routers.admin import _ensure_default_drugs
        _ensure_default_drugs(db)
        # Đảm bảo Sibutramine ở VN là BANNED cho test case này
        db.execute(text("""
            UPDATE drug_country_rules SET status = 'BANNED'
            WHERE drug_id IN (SELECT id FROM drugs WHERE name = 'Sibutramine') AND country_code = 'VN';
        """))
        db.commit()
    finally:
        db.close()

    # Bẫy tin nhắn gửi sang LLM
    captured_messages = []
    monkeypatch.setattr(chat_router.retrieval, "search_chunks", lambda db, q, k=5: [])
    monkeypatch.setattr(ollama_client, "chat", lambda msgs, **kw: captured_messages.extend(msgs) or "CẢNH BÁO: Sibutramine là thuốc bị CẤM tại Việt Nam!")

    try:
        res = client.post("/api/v1/chat/messages", json={"message": "Tôi có nên dùng thuốc Sibutramine để giảm cân không?"}, headers=headers)
        assert res.status_code == 200
        assert "CẢNH BẤO" in res.json()["reply"].upper() or "CẤM" in res.json()["reply"]

        system_prompt = captured_messages[0]["content"]
        assert "QUY TẮC BẮT BUỘC VỀ QUY ĐỊNH DƯỢC PHẨM" in system_prompt
    finally:
        db = SessionLocal()
        db.execute(text("DELETE FROM users WHERE email = :email"), {"email": test_email})
        db.commit()
        db.close()

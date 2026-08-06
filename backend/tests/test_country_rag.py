"""Tests cho RAG & System Prompt."""
import pytest
from app.services.nutrition_context import render_system_prompt

def test_render_system_prompt_basic():
    ctx = {
        "full_name": "Nguyễn Văn A",
        "profile": None,
        "active_plan": None,
        "tracking": None,
    }
    prompt = render_system_prompt(ctx)
    assert "Nguyễn Văn A" in prompt

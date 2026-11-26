"""Bộ chặn câu hỏi ngoài phạm vi (B8): không được từ chối nhầm câu hỏi dinh dưỡng - sức khỏe."""

import json
from pathlib import Path

import pytest

from app.services.accent_restore import strip_accents
from app.services.topic_guard import is_in_scope

QUESTIONS = json.loads((Path(__file__).resolve().parents[1] / "eval" / "rag_questions.json")
                       .read_text(encoding="utf-8"))["questions"]
ON_TOPIC = [q["question"] for q in QUESTIONS if not q.get("off_topic")]


@pytest.mark.parametrize("question", ON_TOPIC)
def test_cau_dung_chu_de_khong_bi_chan_du_rag_rong(question):
    """Bộ 59 câu GĐ2: cả bản có dấu lẫn không dấu đều phải cho qua, kể cả khi RAG không trả gì."""
    assert is_in_scope(question, has_rag_hits=False, in_conversation=False)
    assert is_in_scope(strip_accents(question), has_rag_hits=False, in_conversation=False)


@pytest.mark.parametrize("question", [
    "Cách thay lốp xe máy bị thủng?",
    "cach thay lop xe may bi thung",
    "Viết giúp mình đoạn code Python sắp xếp danh sách",
    "Tỷ số trận bóng tối qua là bao nhiêu?",
    "Thủ đô của nước Pháp là gì?",
])
def test_cau_ngoai_pham_vi_bi_chan(question):
    assert not is_in_scope(question, has_rag_hits=False, in_conversation=False)


def test_co_tai_lieu_lien_quan_thi_luon_cho_qua():
    assert is_in_scope("Thủ đô của nước Pháp là gì?", has_rag_hits=True, in_conversation=False)


def test_cau_noi_tiep_ngan_trong_cuoc_tro_chuyen_duoc_cho_qua():
    assert is_in_scope("Vậy còn buổi tối thì sao?", has_rag_hits=False, in_conversation=True)
    assert not is_in_scope("Vậy còn buổi tối thì sao?", has_rag_hits=False, in_conversation=False)


@pytest.mark.parametrize("greeting", ["Xin chào", "cảm ơn bạn nhé", "Bạn là ai?"])
def test_chao_hoi_duoc_cho_qua(greeting):
    assert is_in_scope(greeting, has_rag_hits=False, in_conversation=False)

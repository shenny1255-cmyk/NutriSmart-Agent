import json
from types import SimpleNamespace

import pytest

from app.services import gemini_vision
from app.services.gemini_vision import analyze_food_image, normalize_food_analysis


def test_tu_choi_anh_khong_phai_mon_an():
    result = normalize_food_analysis({
        "is_food_image": False,
        "food_probability": 0.03,
        "rejection_reason": "Ảnh không chứa món ăn.",
    })

    assert result["is_food_image"] is False
    assert result["food_name"] is None
    assert result["calories_kcal"] is None


def test_thieu_ket_luan_mon_an_thi_tu_choi_an_toan():
    result = normalize_food_analysis({
        "food_name": "Phở bò",
        "calories_kcal": 480,
        "confidence": 0.99,
    })

    assert result["is_food_image"] is False
    assert "không xác nhận" in result["rejection_reason"].lower()


def test_tu_choi_khi_xac_suat_mon_an_duoi_nguong():
    result = normalize_food_analysis({
        "is_food_image": True,
        "food_probability": 0.4,
        "food_name": "Không rõ",
    })

    assert result["is_food_image"] is False


def test_chap_nhan_mon_an_co_du_du_lieu():
    result = normalize_food_analysis({
        "is_food_image": True,
        "food_probability": 0.95,
        "food_name": "Phở bò",
        "calories_kcal": 480,
        "protein_g": 26,
        "carb_g": 58,
        "fat_g": 14,
        "description": "Một tô phở bò.",
        "confidence": 0.9,
    })

    assert result["is_food_image"] is True
    assert result["food_name"] == "Phở bò"
    assert result["calories_kcal"] == 480


def test_mon_an_thieu_du_lieu_dinh_duong_khong_duoc_bia_mac_dinh():
    with pytest.raises(ValueError, match="thiếu dữ liệu"):
        normalize_food_analysis({
            "is_food_image": True,
            "food_probability": 0.95,
            "food_name": "Phở bò",
        })


def test_uu_tien_model_moi_va_fallback_sang_model_con_ho_tro(monkeypatch):
    calls = []
    configs = []

    class FakeModels:
        def generate_content(self, **kwargs):
            calls.append(kwargs["model"])
            configs.append(kwargs["config"])
            if kwargs["model"] != "gemini-3.1-flash-lite":
                raise RuntimeError("model tạm thời không khả dụng")
            return SimpleNamespace(text=json.dumps({
                "is_food_image": True,
                "food_probability": 0.95,
                "food_name": "Phở bò",
                "calories_kcal": 480,
                "protein_g": 26,
                "carb_g": 58,
                "fat_g": 14,
                "description": "Một tô phở bò.",
                "confidence": 0.9,
            }))

    monkeypatch.setattr(gemini_vision.settings, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(
        gemini_vision.genai,
        "Client",
        lambda **_kwargs: SimpleNamespace(models=FakeModels()),
    )

    result = analyze_food_image(b"image")

    assert result["food_name"] == "Phở bò"
    assert calls == ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite"]
    assert all(config.temperature is None for config in configs)


def test_khong_fallback_vao_model_2_0_da_ngung_ho_tro(monkeypatch):
    calls = []

    class FakeModels:
        def generate_content(self, **kwargs):
            calls.append(kwargs["model"])
            raise RuntimeError("model không khả dụng")

    monkeypatch.setattr(gemini_vision.settings, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(
        gemini_vision.genai,
        "Client",
        lambda **_kwargs: SimpleNamespace(models=FakeModels()),
    )

    with pytest.raises(RuntimeError, match="tạm thời không phản hồi"):
        analyze_food_image(b"image")

    assert calls == [
        "gemini-3.5-flash-lite",
        "gemini-3.1-flash-lite",
        "gemini-2.5-flash-lite",
        "gemini-2.5-flash",
    ]

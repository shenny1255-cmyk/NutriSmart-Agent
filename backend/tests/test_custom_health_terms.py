import pytest
from pydantic import ValidationError

from app.schemas import ProfileIn, UserProfileUpdateIn


def profile_data(**extra):
    data = {
        "gender": "MALE", "birth_date": "2000-01-01",
        "height_cm": 170, "weight_kg": 65,
        "activity_level": 3, "goal": "MAINTAIN",
    }
    data.update(extra)
    return data


@pytest.mark.parametrize("term", ["@@@", "🥗", "123456", "aaaaaa", "https://benh.vn", "a@b.com"])
def test_tu_khai_bao_tu_choi_du_lieu_rac(term):
    with pytest.raises(ValidationError):
        ProfileIn(**profile_data(custom_conditions=[term]))


def test_tu_khai_bao_chuan_hoa_va_loai_trung_khong_phan_biet_hoa_thuong():
    profile = ProfileIn(**profile_data(
        custom_conditions=["  Hen phế quản ", "hen PHẾ quản"],
        custom_allergens=["Trứng", " trứng "],
    ))

    assert profile.custom_conditions == ["Hen phế quản"]
    assert len(profile.custom_allergens) == 1
    assert profile.custom_allergens[0].name == "Trứng"


def test_di_ung_tu_khai_bao_luu_muc_do_va_doc_duoc_du_lieu_cu():
    profile = ProfileIn(**profile_data(custom_allergens=[
        {"name": "Hải sản", "severity": "SEVERE"},
        "Trứng",
    ]))

    assert profile.custom_allergens[0].severity == "SEVERE"
    assert profile.custom_allergens[1].severity == "UNKNOWN"


def test_gioi_han_so_muc_tu_khai_bao():
    with pytest.raises(ValidationError):
        UserProfileUpdateIn(custom_allergens=[f"Dị nguyên {i}" for i in range(11)])  # type: ignore[arg-type]

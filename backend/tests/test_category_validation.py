import pytest
from pydantic import ValidationError

from app.schemas import CategoryIn


@pytest.mark.parametrize("name", ["", "a", "@@@", "   ###   ", "Nghiên cứu 🥗", "Y khoa 👩‍⚕️", "a" * 101])
def test_ten_danh_muc_khong_hop_le(name):
    with pytest.raises(ValidationError):
        CategoryIn(name=name)


@pytest.mark.parametrize("name", ["Dinh dưỡng", "Y khoa & sức khỏe", "Đái tháo đường típ 2"])
def test_ten_danh_muc_hop_le(name):
    payload = CategoryIn(name=name)
    assert payload.name == name


def test_ten_danh_muc_duoc_cat_khoang_trang():
    assert CategoryIn(name="  Dinh dưỡng  ").name == "Dinh dưỡng"

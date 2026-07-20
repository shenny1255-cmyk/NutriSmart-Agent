"""Email trên đăng ký/đăng nhập phải chuẩn hoá (thường hoá + trim) và chấp nhận mọi nhà cung cấp."""

import pytest
from pydantic import ValidationError

from app.schemas import RegisterIn, LoginIn


def _profile():
    return {
        "gender": "MALE", "birth_date": "1996-01-01",
        "height_cm": 175, "weight_kg": 72, "activity_level": 3,
        "goal": "MAINTAIN", "condition_ids": [], "allergen_ids": [],
    }


def test_login_email_trimmed_and_lowercased():
    m = LoginIn(email="  User@Gmail.COM  ", password="whatever")
    assert m.email == "user@gmail.com"


def test_register_email_normalized():
    m = RegisterIn(
        email="Foo.Bar+Tag@Example.COM", password="password123",
        full_name="X", country_code="VN", profile=_profile(),
    )
    assert m.email == "foo.bar+tag@example.com"


@pytest.mark.parametrize("email", [
    "user@gmail.com",
    "user+tag@outlook.com",          # +tag
    "user@mail.example.co.uk",       # subdomain / multi-part TLD
    "someone@yahoo.com",
    "nguyen.van.an@company.vn",
    "a@b.io",
])
def test_accepts_all_providers(email):
    # Không chặn bất kỳ nhà cung cấp nào; giá trị trả về là bản thường hoá
    m = LoginIn(email=email, password="x")
    assert m.email == email.lower()


@pytest.mark.parametrize("bad", ["not-an-email", "missing@tld", "@nolocal.com", "spaces in@x.com"])
def test_rejects_invalid_email(bad):
    with pytest.raises(ValidationError):
        LoginIn(email=bad, password="x")

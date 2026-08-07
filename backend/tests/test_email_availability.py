from unittest.mock import MagicMock

from app.routers.auth import check_email_availability
from app.schemas import EmailAvailabilityIn


def test_email_da_ton_tai_thi_khong_kha_dung():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = object()

    result = check_email_availability(EmailAvailabilityIn(email=" Existing@Gmail.COM "), db)

    assert result.available is False


def test_email_chua_ton_tai_thi_kha_dung():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None

    result = check_email_availability(EmailAvailabilityIn(email="new@gmail.com"), db)

    assert result.available is True

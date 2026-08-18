from datetime import date
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.models import User, UserInfo
from app.routers import plans


def _user_with_profile(**overrides) -> User:
    values = {
        "gender": "MALE",
        "birth_date": date(2000, 1, 1),
        "height_cm": 170,
        "weight_kg": 68,
        "activity_level": 3,
        "goal": "MAINTAIN",
        "daily_calorie_target": 2000,
    }
    values.update(overrides)
    user = User(email="profile-plan@test.local", password_hash="x", role="USER")
    user.info = UserInfo(full_name="Người kiểm thử", **values)
    return user


def test_tu_choi_truoc_khi_xep_job_va_liet_ke_truong_ho_so_con_thieu(monkeypatch):
    user = _user_with_profile(height_cm=None, weight_kg=None)

    def must_not_enqueue(_user_id):
        pytest.fail("Không được xếp job khi hồ sơ còn thiếu")

    monkeypatch.setattr(plans.plan_jobs, "enqueue", must_not_enqueue)

    with pytest.raises(HTTPException) as exc_info:
        plans.generate_plan(db=object(), user=user)

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == (
        "Bạn chưa cập nhật chiều cao và cân nặng. "
        "Vui lòng hoàn thiện hồ sơ trước khi tạo lộ trình."
    )


def test_ho_so_day_du_moi_duoc_xep_job(monkeypatch):
    user = _user_with_profile()
    queued = SimpleNamespace(id="job-test", status="QUEUED")
    monkeypatch.setattr(plans.plan_jobs, "enqueue", lambda user_id: queued)

    result = plans.generate_plan(db=object(), user=user)

    assert result == {"job_id": "job-test", "status": "QUEUED"}

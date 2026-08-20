from datetime import date
from types import SimpleNamespace
from typing import cast
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import BodyMetricHistory, User, UserProfile
from app.routers import plans
from app.schemas import PlanGenerateIn


FAKE_DB = cast(Session, object())


def _user_with_profile(**overrides) -> tuple[User, BodyMetricHistory]:
    height_cm = overrides.pop("height_cm", 170)
    weight_kg = overrides.pop("weight_kg", 68)
    values = {
        "gender": "MALE",
        "birth_date": date(2000, 1, 1),
        "activity_level": 3,
        "goal": "MAINTAIN",
        "daily_calorie_target": 2000,
    }
    values.update(overrides)
    user = User(id=uuid4(), email="profile-plan@test.local", password_hash="x", role="USER")
    user.profile = UserProfile(full_name="Người kiểm thử", **values)
    metric = BodyMetricHistory(
        user_id=user.id,
        height_cm=height_cm,
        weight_kg=weight_kg,
    )
    return user, metric


def test_tu_choi_truoc_khi_xep_job_va_liet_ke_truong_ho_so_con_thieu(monkeypatch):
    user, metric = _user_with_profile(height_cm=None, weight_kg=None)

    def must_not_enqueue(_user_id):
        pytest.fail("Không được xếp job khi hồ sơ còn thiếu")

    monkeypatch.setattr(plans.plan_jobs, "enqueue", must_not_enqueue)
    monkeypatch.setattr(plans.body_metrics, "latest_body_metric", lambda _db, _user_id: metric)

    with pytest.raises(HTTPException) as exc_info:
        plans.generate_plan(
            payload=PlanGenerateIn(height_cm=170, weight_kg=68),
            db=FAKE_DB,
            user=user,
        )

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == (
        "Bạn chưa cập nhật chiều cao và cân nặng. "
        "Vui lòng hoàn thiện hồ sơ trước khi tạo lộ trình."
    )


def test_ho_so_day_du_moi_duoc_xep_job(monkeypatch):
    user, metric = _user_with_profile()
    queued = SimpleNamespace(id="job-test", status="QUEUED")
    monkeypatch.setattr(plans.plan_jobs, "enqueue", lambda user_id, **kwargs: queued)
    monkeypatch.setattr(plans.body_metrics, "latest_body_metric", lambda _db, _user_id: metric)
    monkeypatch.setattr(plans.plan_evaluator, "active_plan", lambda _db, _user: None)
    monkeypatch.setattr(
        plans,
        "_save_generation_metrics",
        lambda *_args, **_kwargs: (2000, {"goal": "MAINTAIN"}),
    )

    result = plans.generate_plan(
        payload=PlanGenerateIn(height_cm=170, weight_kg=68),
        db=FAKE_DB,
        user=user,
    )

    assert result == {"job_id": "job-test", "status": "QUEUED"}


def test_tao_lai_can_xac_nhan_va_dung_active_plan_du_kien(monkeypatch):
    user, metric = _user_with_profile()
    active_id = uuid4()
    active = SimpleNamespace(id=active_id)
    monkeypatch.setattr(plans.body_metrics, "latest_body_metric", lambda _db, _user_id: metric)
    monkeypatch.setattr(plans.plan_evaluator, "active_plan", lambda _db, _user: active)

    with pytest.raises(HTTPException) as missing_confirm:
        plans.generate_plan(
            payload=PlanGenerateIn(height_cm=170, weight_kg=68), db=FAKE_DB, user=user,
        )
    assert missing_confirm.value.status_code == 409

    with pytest.raises(HTTPException) as stale_plan:
        plans.generate_plan(
            payload=PlanGenerateIn(
                height_cm=170,
                weight_kg=68,
                confirm_recreate=True,
                expected_active_plan_id=uuid4(),
            ),
            db=FAKE_DB,
            user=user,
        )
    assert stale_plan.value.status_code == 409


def test_tao_chuong_trinh_chan_can_nang_lech_qua_muoi_phan_tram(monkeypatch):
    user, metric = _user_with_profile(weight_kg=70)
    monkeypatch.setattr(plans.body_metrics, "latest_body_metric", lambda _db, _user_id: metric)
    monkeypatch.setattr(plans.plan_evaluator, "active_plan", lambda _db, _user: None)

    with pytest.raises(HTTPException) as exc_info:
        plans.generate_plan(
            payload=PlanGenerateIn(height_cm=170, weight_kg=80), db=FAKE_DB, user=user,
        )

    assert exc_info.value.status_code == 422
    assert "10%" in exc_info.value.detail

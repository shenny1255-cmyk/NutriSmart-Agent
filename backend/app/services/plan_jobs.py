"""Tác vụ nền sinh lộ trình, dùng SessionLocal riêng cho worker."""

import logging
import threading
import uuid
from dataclasses import dataclass
from datetime import date

from app.database import SessionLocal
from app.models import NutritionPlan, User
from app.services import plan_checkin, plan_generator

log = logging.getLogger("nutrismart.plan_jobs")


@dataclass
class PlanJob:
    id: str
    user_id: uuid.UUID
    status: str = "QUEUED"
    plan_id: uuid.UUID | None = None
    error: str | None = None
    target_kcal: int | None = None
    duration_months: int = 3
    expected_active_plan_id: uuid.UUID | None = None
    profile_data: dict | None = None
    baseline_weight_kg: float | None = None


_jobs: dict[str, PlanJob] = {}
_user_jobs: dict[uuid.UUID, str] = {}
_lock = threading.Lock()


def _run(job_id: str) -> None:
    with _lock:
        job = _jobs[job_id]
        job.status = "RUNNING"

    db = None
    try:
        db = SessionLocal()
        user = db.query(User).filter(User.id == job.user_id).first()  # type: ignore
        if not user or not user.profile:
            raise ValueError("Chưa có hồ sơ sức khỏe")
        active = (
            db.query(NutritionPlan)
            .filter(
                NutritionPlan.user_id == user.id,
                NutritionPlan.status == "ACTIVE",  # type: ignore
            )
            .with_for_update()
            .first()
        )
        actual_active_id = active.id if active else None
        if actual_active_id != job.expected_active_plan_id:
            raise RuntimeError("Lộ trình hiện tại đã thay đổi; vui lòng tải lại trang")

        today = date.today()
        end_date = plan_checkin.program_end_date(today, job.duration_months)
        plan = plan_generator.create_plan(
            db,
            user,
            target=job.target_kcal,
            start_date=today,
            end_date=end_date,
            profile_data=job.profile_data,
        )
        db.flush()
        plan_checkin.start_new_series(
            db,
            user,
            plan,
            today=today,
            duration_months=job.duration_months,
            baseline_weight_kg=job.baseline_weight_kg,
        )
        db.commit()
        with _lock:
            job.status = "DONE"
            job.plan_id = plan.id
    except Exception as e:  # noqa: BLE001 — trạng thái lỗi trả về cho UI
        if db is not None:
            db.rollback()
        log.exception("Lỗi job sinh lộ trình %s", job_id)
        with _lock:
            job.status = "FAILED"
            job.error = str(e)
    finally:
        if db is not None:
            db.close()
        with _lock:
            if _user_jobs.get(job.user_id) == job_id:
                del _user_jobs[job.user_id]


def enqueue(
    user_id: uuid.UUID,
    *,
    target_kcal: int | None = None,
    duration_months: int = 3,
    expected_active_plan_id: uuid.UUID | None = None,
    profile_data: dict | None = None,
    baseline_weight_kg: float | None = None,
) -> PlanJob:
    with _lock:
        existing_id = _user_jobs.get(user_id)
        if existing_id:
            return _jobs[existing_id]
        job = PlanJob(
            id=uuid.uuid4().hex,
            user_id=user_id,
            target_kcal=target_kcal,
            duration_months=duration_months,
            expected_active_plan_id=expected_active_plan_id,
            profile_data=profile_data,
            baseline_weight_kg=baseline_weight_kg,
        )
        _jobs[job.id] = job
        _user_jobs[user_id] = job.id
    worker = threading.Thread(target=_run, args=(job.id,), daemon=True)
    try:
        worker.start()
    except Exception:
        with _lock:
            _jobs.pop(job.id, None)
            if _user_jobs.get(user_id) == job.id:
                _user_jobs.pop(user_id, None)
        raise
    return job


def get(job_id: str, user_id: uuid.UUID) -> PlanJob | None:
    with _lock:
        job = _jobs.get(job_id)
        if job and job.user_id == user_id:
            return job
        return None

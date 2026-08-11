"""Tác vụ nền sinh lộ trình, dùng SessionLocal riêng cho worker."""

import logging
import threading
import uuid
from dataclasses import dataclass

from app.database import SessionLocal
from app.models import User
from app.services import plan_checkin, plan_generator

log = logging.getLogger("nutrismart.plan_jobs")


@dataclass
class PlanJob:
    id: str
    user_id: uuid.UUID
    status: str = "QUEUED"
    plan_id: uuid.UUID | None = None
    error: str | None = None


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
        if not user or not user.info:
            raise ValueError("Chưa có hồ sơ sức khỏe")
        plan = plan_generator.create_plan(db, user)
        db.flush()
        plan_checkin.start_new_series(db, user, plan)
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


def enqueue(user_id: uuid.UUID) -> PlanJob:
    with _lock:
        existing_id = _user_jobs.get(user_id)
        if existing_id:
            return _jobs[existing_id]
        job = PlanJob(id=uuid.uuid4().hex, user_id=user_id)
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

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

from hermes_orchestrator.ollama_manage import OllamaManageError, pull_model

PullJobStatus = Literal["pending", "running", "succeeded", "failed"]


@dataclass
class PullJob:
    job_id: str
    model: str
    host: str
    status: PullJobStatus = "pending"
    error: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    finished_at: str | None = None


_LOCK = threading.Lock()
_JOBS: dict[str, PullJob] = {}


def start_pull_job(*, model: str, host: str) -> PullJob:
    job_id = str(uuid.uuid4())
    job = PullJob(job_id=job_id, model=model.strip(), host=host)
    with _LOCK:
        _JOBS[job_id] = job

    def _run() -> None:
        with _LOCK:
            job.status = "running"
        try:
            pull_model(job.model, host=job.host)
        except OllamaManageError as exc:
            with _LOCK:
                job.status = "failed"
                job.error = str(exc)
                job.finished_at = datetime.now(timezone.utc).isoformat()
            return
        with _LOCK:
            job.status = "succeeded"
            job.finished_at = datetime.now(timezone.utc).isoformat()

    threading.Thread(target=_run, name=f"ollama-pull-{job_id[:8]}", daemon=True).start()
    return job


def get_pull_job(job_id: str) -> PullJob | None:
    with _LOCK:
        return _JOBS.get(job_id)


def reset_pull_jobs_for_tests() -> None:
    with _LOCK:
        _JOBS.clear()

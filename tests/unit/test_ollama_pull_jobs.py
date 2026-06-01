from __future__ import annotations

import time
from unittest.mock import patch

from hermes_orchestrator.ollama_pull_jobs import get_pull_job, reset_pull_jobs_for_tests, start_pull_job


def test_start_pull_job_completes_successfully() -> None:
    reset_pull_jobs_for_tests()
    with patch("hermes_orchestrator.ollama_pull_jobs.pull_model") as pull:
        job = start_pull_job(model="tiny", host="http://127.0.0.1:11434")
        current = None
        for _ in range(100):
            current = get_pull_job(job.job_id)
            if current and current.status in {"succeeded", "failed"}:
                break
            time.sleep(0.02)
    assert current is not None
    assert current.status == "succeeded"
    pull.assert_called_once_with("tiny", host="http://127.0.0.1:11434")

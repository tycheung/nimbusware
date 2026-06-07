"""Redis dispatch worker stack — API + worker subprocesses share Redis queue."""

from __future__ import annotations

import os
import time
from pathlib import Path

import httpx
import pytest

from e2e.harness.stack import (
    start_api_subprocess,
    start_worker_subprocess,
    stop_api_subprocess,
    stop_worker_subprocess,
)
from nimbusware_env import find_repo_root
from nimbusware_env.admin_token import DEFAULT_NIMBUSWARE_ADMIN_TOKEN

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.e2e_stack,
    pytest.mark.integration,
]

_FIXTURE_WS = Path(__file__).resolve().parents[1] / "fixtures" / "repos" / "tiny_python_app"
_ADMIN = {"X-Nimbusware-Admin-Token": DEFAULT_NIMBUSWARE_ADMIN_TOKEN}


def _redis_reachable(url: str) -> bool:
    try:
        import redis
    except ImportError:
        return False
    try:
        client = redis.Redis.from_url(url, decode_responses=True, socket_connect_timeout=1.0)
        client.ping()
        return True
    except Exception:
        return False


@pytest.fixture
def redis_url() -> str:
    url = os.environ.get("NIMBUSWARE_REDIS_URL", "redis://127.0.0.1:6379/0").strip()
    if not _redis_reachable(url):
        pytest.skip(f"Redis not reachable at {url}")
    return url


def test_redis_dispatch_worker_subprocess_drains_campaign_queue(redis_url: str) -> None:
    repo = find_repo_root()
    env = {
        "NIMBUSWARE_RUN_DISPATCH": "redis",
        "NIMBUSWARE_REDIS_URL": redis_url,
    }
    worker = start_worker_subprocess(repo, env=env)
    stack = start_api_subprocess(repo, env=env)
    try:
        project = httpx.post(
            f"{stack.base_url}/v1/projects",
            json={
                "name": "redis-dispatch-worker",
                "workspace_path": str(_FIXTURE_WS.resolve()),
                "template": "attach",
            },
            headers=_ADMIN,
            timeout=30.0,
        )
        assert project.status_code == 200, project.text
        project_id = project.json()["project_id"]
        created = httpx.post(
            f"{stack.base_url}/v1/campaigns",
            json={
                "project_id": project_id,
                "requirements": {"business_prompt": "redis worker stack"},
                "autonomous": True,
                "workflow_profile": "campaign_micro_slice",
            },
            headers=_ADMIN,
            timeout=30.0,
        )
        assert created.status_code == 200, created.text
        body = created.json()
        assert body.get("dispatch_mode") == "queued"
        run_id = str(body["run_id"])
        deadline = time.monotonic() + 90.0
        saw_backlog = False
        while time.monotonic() < deadline:
            timeline = httpx.get(
                f"{stack.base_url}/v1/runs/{run_id}/timeline",
                timeout=30.0,
            )
            assert timeline.status_code == 200, timeline.text
            types = {e.get("event_type") for e in timeline.json().get("events", [])}
            if "delivery_backlog.generated" in types or "slice.queued" in types:
                saw_backlog = True
                break
            time.sleep(0.25)
        assert saw_backlog
    finally:
        stop_api_subprocess(stack)
        stop_worker_subprocess(worker)

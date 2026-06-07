"""Campaign dispatch worker journey — uvicorn subprocess with embedded worker thread."""

from __future__ import annotations

import time
from pathlib import Path

import httpx
import pytest

from e2e.harness.stack import start_api_subprocess, stop_api_subprocess
from nimbusware_env import find_repo_root
from nimbusware_env.admin_token import DEFAULT_NIMBUSWARE_ADMIN_TOKEN

pytestmark = [pytest.mark.e2e, pytest.mark.e2e_journey, pytest.mark.e2e_stack]

_FIXTURE_WS = Path(__file__).resolve().parents[2] / "fixtures" / "repos" / "tiny_python_app"
_ADMIN = {"X-Nimbusware-Admin-Token": DEFAULT_NIMBUSWARE_ADMIN_TOKEN}


def test_campaign_subprocess_embed_dispatch_worker_generates_backlog() -> None:
    repo = find_repo_root()
    stack = start_api_subprocess(
        repo,
        env={
            "NIMBUSWARE_RUN_DISPATCH": "memory",
            "NIMBUSWARE_EMBED_DISPATCH_WORKER": "1",
        },
    )
    try:
        project = httpx.post(
            f"{stack.base_url}/v1/projects",
            json={
                "name": "subprocess-dispatch-worker",
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
                "requirements": {"business_prompt": "subprocess embed worker"},
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
        deadline = time.monotonic() + 60.0
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

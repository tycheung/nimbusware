from __future__ import annotations

import time
from pathlib import Path

import httpx
import pytest

from e2e.harness.stack import start_api_subprocess, stop_api_subprocess
from nimbusware_env import find_repo_root
from nimbusware_env.admin_token import DEFAULT_NIMBUSWARE_ADMIN_TOKEN

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.e2e_journey,
    pytest.mark.e2e_stack,
    pytest.mark.slow,
]

_FIXTURE_WS = Path(__file__).resolve().parents[2] / "fixtures" / "repos" / "tiny_python_app"
_ADMIN = {"X-Nimbusware-Admin-Token": DEFAULT_NIMBUSWARE_ADMIN_TOKEN}
_SOAK_SECONDS = 45.0


def test_full_replay_stack_soak_campaign_and_launch_eval() -> None:
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
                "name": "full-replay-stack-soak",
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
                "requirements": {
                    "business_prompt": "Build a minimal CRM with user authentication",
                },
                "autonomous": True,
                "workflow_profile": "campaign_micro_slice",
            },
            headers=_ADMIN,
            timeout=30.0,
        )
        assert created.status_code == 200, created.text
        run_id = str(created.json()["run_id"])
        deadline = time.monotonic() + _SOAK_SECONDS
        saw_progress = False
        while time.monotonic() < deadline:
            progress = httpx.get(
                f"{stack.base_url}/v1/runs/{run_id}/maker-progress?simple=true",
                timeout=30.0,
            )
            assert progress.status_code == 200, progress.text
            body = progress.json()
            if int(body.get("campaign_progress", {}).get("slices_total") or 0) > 0:
                saw_progress = True
                break
            time.sleep(0.5)
        assert saw_progress, "campaign progress did not appear during soak window"
        launch = httpx.post(
            f"{stack.base_url}/v1/runs/{run_id}/maker/launch-eval",
            headers=_ADMIN,
            timeout=60.0,
        )
        assert launch.status_code == 200, launch.text
        scorecard = launch.json()
        assert scorecard.get("aggregate", 0) > 0
        assert scorecard.get("attach_context", {}).get("prompt_id") == "basic_crm"
    finally:
        stop_api_subprocess(stack)

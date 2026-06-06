"""Stack E2E with subprocess uvicorn and Postgres."""

from __future__ import annotations

import os

import httpx
import pytest

from e2e.harness.stack import start_api_subprocess, stop_api_subprocess
from nimbusware_env import find_repo_root

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.e2e_stack,
    pytest.mark.integration,
]


@pytest.fixture
def postgres_url() -> str:
    url = os.environ.get("NIMBUSWARE_DATABASE_URL", "").strip()
    if not url:
        pytest.skip("NIMBUSWARE_DATABASE_URL not set")
    return url


def test_timeline_survives_api_restart(postgres_url: str) -> None:
    repo = find_repo_root()
    env = {
        "NIMBUSWARE_DATABASE_URL": postgres_url,
        "NIMBUSWARE_SLICE_IMPLEMENT": "stub",
        "NIMBUSWARE_SLICE_AUTO_ADVANCE": "0",
        "NIMBUSWARE_MICRO_SLICE_COUNT": "1",
    }
    stack = start_api_subprocess(repo, env=env)
    try:
        created = httpx.post(
            f"{stack.base_url}/v1/runs",
            json={"workflow_profile": "default"},
            timeout=30.0,
        )
        assert created.status_code == 200, created.text
        run_id = created.json()["run_id"]
        timeline1 = httpx.get(f"{stack.base_url}/v1/runs/{run_id}/timeline", timeout=30.0)
        assert timeline1.status_code == 200
        count1 = len(timeline1.json().get("events") or [])
        assert count1 >= 1
    finally:
        stop_api_subprocess(stack)

    stack2 = start_api_subprocess(repo, env=env)
    try:
        timeline2 = httpx.get(f"{stack.base_url}/v1/runs/{run_id}/timeline", timeout=30.0)
        assert timeline2.status_code == 200
        count2 = len(timeline2.json().get("events") or [])
        assert count2 >= count1
    finally:
        stop_api_subprocess(stack2)

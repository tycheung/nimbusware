from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

import httpx
import pytest

from e2e.harness.stack import start_api_subprocess, stop_api_subprocess
from nimbusware_env import find_repo_root
from nimbusware_env.admin_token import DEFAULT_NIMBUSWARE_ADMIN_TOKEN

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.e2e_journey,
    pytest.mark.e2e_stack,
    pytest.mark.integration,
]

_FIXTURE_WS = Path(__file__).resolve().parents[2] / "fixtures" / "repos" / "tiny_python_app"
_ADMIN = {"X-Nimbusware-Admin-Token": DEFAULT_NIMBUSWARE_ADMIN_TOKEN}


@pytest.fixture
def postgres_url() -> str:
    url = os.environ.get("NIMBUSWARE_DATABASE_URL", "").strip()
    if not url:
        pytest.skip("NIMBUSWARE_DATABASE_URL not set")
    return url


def test_chat_session_and_analytics_survive_api_restart(postgres_url: str) -> None:
    repo = find_repo_root()
    env = {
        "NIMBUSWARE_DATABASE_URL": postgres_url,
        "NIMBUSWARE_SLICE_IMPLEMENT": "stub",
        "NIMBUSWARE_SKIP_PREFLIGHT": "1",
    }
    stack = start_api_subprocess(repo, env=env)
    session_id: str | None = None
    try:
        project = httpx.post(
            f"{stack.base_url}/v1/projects",
            json={
                "name": f"chat-pg-{uuid4().hex[:8]}",
                "workspace_path": str(_FIXTURE_WS.resolve()),
                "template": "attach",
            },
            headers=_ADMIN,
            timeout=30.0,
        )
        assert project.status_code == 200, project.text
        project_id = project.json()["project_id"]

        session = httpx.post(
            f"{stack.base_url}/v1/chat/sessions",
            json={"project_id": project_id},
            timeout=30.0,
        )
        assert session.status_code == 200, session.text
        session_id = session.json()["session_id"]

        turn = httpx.post(
            f"{stack.base_url}/v1/chat/sessions/{session_id}/turns",
            json={"text": "fix postgres persistence test", "role": "user"},
            timeout=30.0,
        )
        assert turn.status_code == 200, turn.text

        analytics = httpx.get(
            f"{stack.base_url}/v1/platform/analytics/chat-turns?limit_sessions=20",
            timeout=30.0,
        )
        assert analytics.status_code == 200, analytics.text
        body = analytics.json()
        assert int(body.get("turn_count") or 0) >= 1
        assert int(body.get("sessions_scanned") or 0) >= 1
    finally:
        stop_api_subprocess(stack)

    assert session_id
    stack2 = start_api_subprocess(repo, env=env, port=stack.port)
    try:
        loaded = httpx.get(
            f"{stack2.base_url}/v1/chat/sessions/{session_id}?include_turns=true",
            timeout=30.0,
        )
        assert loaded.status_code == 200, loaded.text
        messages = loaded.json().get("messages") or []
        assert any("postgres persistence" in str(m.get("text") or "") for m in messages)

        analytics2 = httpx.get(
            f"{stack2.base_url}/v1/platform/analytics/chat-turns?limit_sessions=20",
            timeout=30.0,
        )
        assert analytics2.status_code == 200
        assert int(analytics2.json().get("turn_count") or 0) >= 1
    finally:
        stop_api_subprocess(stack2)

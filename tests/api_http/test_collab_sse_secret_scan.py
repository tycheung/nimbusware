from __future__ import annotations

import json
import re
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.slow

_SECRET_A = "sk-host-secret-aaaaaaaaaaaaaaaa"
_SECRET_B = "sk-guest-secret-bbbbbbbbbbbbbbbb"


def _enable_collab(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_COLLAB_ENABLED", "1")


def _signup(client: TestClient, username: str) -> dict:
    resp = client.post(
        "/v1/auth/signup",
        json={"username": username, "password": "password1234", "display_name": username},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def _create_project(client: TestClient, tmp_path: Path) -> str:
    ws = tmp_path / "collab-sse"
    ws.mkdir()
    resp = client.post(
        "/v1/projects",
        json={
            "name": "collab-sse",
            "workspace_path": str(ws),
            "template": "attach",
            "default_workflow_profile": "micro_slice",
        },
    )
    assert resp.status_code == 200
    return resp.json()["project_id"]


def _parse_sse_chunks(text: str) -> list[dict]:
    events: list[dict] = []
    for block in re.split(r"\n\n+", text.strip()):
        if not block.strip():
            continue
        data_line = next(
            (ln[5:].strip() for ln in block.splitlines() if ln.startswith("data:")), ""
        )
        if data_line:
            events.append(json.loads(data_line))
    return events


def test_collab_session_sse_redacts_theater_secrets(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _enable_collab(monkeypatch)
    _signup(client, f"host-{uuid4().hex[:8]}")
    guest = _signup(client, f"guest-{uuid4().hex[:8]}")
    project_id = _create_project(client, tmp_path)
    sess = client.post("/v1/chat/sessions", json={"project_id": project_id})
    assert sess.status_code == 200
    session_id = UUID(sess.json()["session_id"])
    client.post(
        f"/v1/chat/sessions/{session_id}/participants",
        json={"user_id": guest["user_id"], "role": "session_read"},
    )

    chat_store = client.app.state.chat_store
    chat_store.append_turn(
        session_id,
        role="theater",
        text=f"Planner used api_key={_SECRET_A} on host node",
    )
    chat_store.append_turn(
        session_id,
        role="theater",
        text=f"Guest probe bearer {_SECRET_B}",
    )

    client.post("/v1/auth/signout")
    client.post(
        "/v1/auth/signin",
        json={"username": guest["username"], "password": "password1234"},
    )

    with client.stream("GET", f"/v1/chat/sessions/{session_id}/stream") as resp:
        assert resp.status_code == 200
        chunk = next(resp.iter_text())
        assert _SECRET_A not in chunk
        assert _SECRET_B not in chunk
        assert "[redacted]" in chunk
        events = _parse_sse_chunks(chunk)
        theater = events[0].get("theater_lines") if events else []
        assert isinstance(theater, list)
        joined = json.dumps(theater)
        assert _SECRET_A not in joined
        assert _SECRET_B not in joined


def test_collab_two_vaults_participant_bindings_isolated(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _enable_collab(monkeypatch)
    _signup(client, f"host-{uuid4().hex[:8]}")
    guest = _signup(client, f"guest-{uuid4().hex[:8]}")
    project_id = _create_project(client, tmp_path)
    sess = client.post("/v1/chat/sessions", json={"project_id": project_id})
    session_id = sess.json()["session_id"]
    client.post(
        f"/v1/chat/sessions/{session_id}/participants",
        json={"user_id": guest["user_id"], "role": "session_write"},
    )

    client.put(
        f"/v1/chat/sessions/{session_id}/participant-bindings",
        json={
            "agent_role": "planner",
            "provider_kind": "cloud",
            "provider_id": "openai",
            "model_id": "gpt-4o-mini",
            "connection_id": "00000000-0000-4000-8000-000000000001",
        },
    )
    client.post("/v1/auth/signout")
    client.post(
        "/v1/auth/signin",
        json={"username": guest["username"], "password": "password1234"},
    )
    guest_put = client.put(
        f"/v1/chat/sessions/{session_id}/participant-bindings",
        json={
            "agent_role": "planner",
            "provider_kind": "cloud",
            "provider_id": "anthropic",
            "model_id": "claude-3-5-sonnet",
            "connection_id": "00000000-0000-4000-8000-000000000002",
        },
    )
    assert guest_put.status_code == 200
    guest_bindings = client.get(f"/v1/chat/sessions/{session_id}/participant-bindings")
    assert guest_bindings.status_code == 200
    roles = guest_bindings.json().get("roles") or {}
    assert roles.get("planner", {}).get("provider_id") == "anthropic"
    assert _SECRET_A not in guest_bindings.text
    assert _SECRET_B not in guest_bindings.text

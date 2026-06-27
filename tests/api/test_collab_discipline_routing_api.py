from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.slow


def _enable_collab(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_COLLAB_ENABLED", "1")


def _signup(client: TestClient, username: str) -> str:
    resp = client.post(
        "/v1/auth/signup",
        json={"username": username, "password": "password1234", "display_name": username.title()},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["user_id"]


def _signin(client: TestClient, username: str) -> None:
    resp = client.post(
        "/v1/auth/signin",
        json={"username": username, "password": "password1234"},
    )
    assert resp.status_code == 200, resp.text


def test_commentary_routes_discipline_to_interjection_queue(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _enable_collab(monkeypatch)
    _signup(client, "routehost")
    _signin(client, "routehost")
    ws = tmp_path / "collab-route-app"
    ws.mkdir()
    project_id = client.post(
        "/v1/projects",
        json={
            "name": "Route demo",
            "workspace_path": str(ws),
            "template": "attach",
            "default_workflow_profile": "micro_slice",
        },
    ).json()["project_id"]
    session_id = client.post(
        "/v1/chat/sessions",
        json={"project_id": project_id},
    ).json()["session_id"]

    started = client.post(
        f"/v1/chat/sessions/{session_id}/start",
        json={
            "work_type": "slice",
            "workflow_profile": "micro_slice",
            "requirements": {"business_prompt": "fix the dashboard"},
        },
    )
    assert started.status_code == 200, started.text
    run_id = started.json()["run_id"]
    assert run_id

    guest_id = _signup(client, "routeguest")
    _signin(client, "routehost")
    added = client.post(
        f"/v1/chat/sessions/{session_id}/participants",
        json={"user_id": guest_id, "role": "session_write", "user_discipline": "qa"},
    )
    assert added.status_code == 200

    _signin(client, "routeguest")
    commentary = client.post(
        f"/v1/chat/sessions/{session_id}/commentary",
        json={"text": "@frontend please fix the dashboard layout"},
    )
    assert commentary.status_code == 200, commentary.text
    routes = commentary.json().get("discipline_routes")
    assert isinstance(routes, list)
    assert routes[0]["discipline"] == "frontend"
    assert routes[0]["taxonomy_key"] == "frontend_writer"

    queue = client.get(f"/v1/runs/{run_id}/interjection-queue")
    assert queue.status_code == 200
    items = queue.json()["queue"]["items"]
    assert items
    assert items[0]["taxonomy_key"] == "frontend_writer"

    session = client.get(f"/v1/chat/sessions/{session_id}?include_turns=true")
    assert session.status_code == 200
    turns = session.json().get("turns") or []
    routed = [t for t in turns if (t.get("payload") or {}).get("kind") == "discipline_route"]
    assert routed
    assert "frontend_writer" in routed[-1]["text"]


def test_participant_context_round_trip(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    _enable_collab(monkeypatch)
    _signup(client, "ctxuser")
    saved = client.put(
        "/v1/users/me/participant-context",
        json={"expertise_bullets": ["React perf", "a11y"]},
    )
    assert saved.status_code == 200
    assert saved.json()["expertise_bullets"] == ["React perf", "a11y"]
    loaded = client.get("/v1/users/me/participant-context")
    assert loaded.status_code == 200
    assert loaded.json()["expertise_bullets"] == ["React perf", "a11y"]

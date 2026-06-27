from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.slow


def _enable_collab(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_COLLAB_ENABLED", "1")


def _signup(client: TestClient, username: str, password: str = "password1234") -> None:
    resp = client.post(
        "/v1/auth/signup",
        json={"username": username, "password": password, "display_name": username.title()},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["username"] == username.lower()


def _create_project(client: TestClient, tmp_path: Path) -> str:
    ws = tmp_path / "collab-app"
    ws.mkdir()
    resp = client.post(
        "/v1/projects",
        json={
            "name": "Collab demo",
            "workspace_path": str(ws),
            "template": "attach",
            "default_workflow_profile": "micro_slice",
        },
    )
    assert resp.status_code == 200
    return resp.json()["project_id"]


def test_participants_invite_and_join(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _enable_collab(monkeypatch)
    _signup(client, "host")
    project_id = _create_project(client, tmp_path)
    session_id = client.post(
        "/v1/chat/sessions",
        json={"project_id": project_id, "folder": "Q2 patches"},
    ).json()["session_id"]

    parts = client.get(f"/v1/chat/sessions/{session_id}/participants")
    assert parts.status_code == 200
    assert len(parts.json()) == 1
    assert parts.json()[0]["role"] == "session_admin"

    detail = client.get(f"/v1/chat/sessions/{session_id}")
    assert detail.json()["metadata"]["folder"] == "Q2 patches"

    invite = client.post(
        f"/v1/chat/sessions/{session_id}/invites",
        json={"role": "session_read", "expires_hours": 24},
    )
    assert invite.status_code == 200
    token = invite.json()["join_url"].rsplit("/", 1)[-1]

    client.post("/v1/auth/signout")
    _signup(client, "guest")

    joined = client.post("/v1/chat/join", json={"token": token, "user_discipline": "qa"})
    assert joined.status_code == 200
    assert joined.json()["role"] == "session_read"

    guests = client.get(f"/v1/chat/sessions/{session_id}/participants")
    assert guests.status_code == 200
    assert len(guests.json()) == 2
    guest_row = next(p for p in guests.json() if p.get("username") == "guest")
    assert guest_row.get("user_discipline") == "qa"


def test_join_preview_and_discipline_profile(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _enable_collab(monkeypatch)
    _signup(client, "host2")
    project_id = _create_project(client, tmp_path)
    session_id = client.post(
        "/v1/chat/sessions",
        json={"project_id": project_id},
    ).json()["session_id"]
    invite = client.post(
        f"/v1/chat/sessions/{session_id}/invites",
        json={"role": "session_write", "recommended_discipline": "frontend"},
    )
    assert invite.status_code == 200
    token = invite.json()["join_url"].rsplit("/", 1)[-1]
    preview = client.get(f"/v1/chat/join-preview?token={token}")
    assert preview.status_code == 200
    assert preview.json()["recommended_discipline"] == "frontend"

    profile = client.put(
        "/v1/users/me/discipline-profile",
        json={"default_discipline": "backend"},
    )
    assert profile.status_code == 200
    assert profile.json()["default_discipline"] == "backend"

    catalog = client.get("/v1/platform/collab-disciplines")
    assert catalog.status_code == 200
    assert any(d["id"] == "frontend" for d in catalog.json()["disciplines"])


def test_read_only_cannot_post_turn(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _enable_collab(monkeypatch)
    _signup(client, "owner")
    project_id = _create_project(client, tmp_path)
    session_id = client.post("/v1/chat/sessions", json={"project_id": project_id}).json()[
        "session_id"
    ]

    invite = client.post(
        f"/v1/chat/sessions/{session_id}/invites",
        json={"role": "session_read"},
    ).json()
    token = invite["join_url"].rsplit("/", 1)[-1]

    client.post("/v1/auth/signout")
    _signup(client, "reader")
    client.post("/v1/chat/join", json={"token": token})

    denied = client.post(
        f"/v1/chat/sessions/{session_id}/messages",
        json={"text": "I should not post"},
    )
    assert denied.status_code == 403
    assert denied.json()["code"] == "forbidden"


def test_admin_adds_write_participant(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _enable_collab(monkeypatch)
    _signup(client, "admin")
    project_id = _create_project(client, tmp_path)
    session_id = client.post("/v1/chat/sessions", json={"project_id": project_id}).json()[
        "session_id"
    ]

    client.post("/v1/auth/signout")
    _signup(client, "writer")

    me = client.get("/v1/auth/me").json()
    writer_id = me["user_id"]

    client.post("/v1/auth/signout")
    client.post("/v1/auth/signin", json={"username": "admin", "password": "password1234"})

    added = client.post(
        f"/v1/chat/sessions/{session_id}/participants",
        json={"user_id": writer_id, "role": "session_write"},
    )
    assert added.status_code == 200
    assert added.json()["role"] == "session_write"

    client.post("/v1/auth/signout")
    client.post("/v1/auth/signin", json={"username": "writer", "password": "password1234"})

    ok = client.post(
        f"/v1/chat/sessions/{session_id}/messages",
        json={"text": "writer can post"},
    )
    assert ok.status_code == 200

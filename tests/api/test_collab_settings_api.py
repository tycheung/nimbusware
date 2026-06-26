from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient


def test_collab_settings_toggle_without_env_restart(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from nimbusware_config import collab_settings_store

    monkeypatch.setattr(
        collab_settings_store,
        "collab_settings_path",
        lambda repo_root=None: tmp_path / "collab_settings.yaml",
    )
    monkeypatch.setenv("NIMBUSWARE_COLLAB_ENABLED", "1")
    from nimbusware_env.collab_runtime import set_runtime_collab_enabled

    set_runtime_collab_enabled(True)
    username = f"collab-settings-{uuid4().hex[:8]}"
    signup = client.post(
        "/v1/auth/signup",
        json={
            "username": username,
            "password": "password1234",
            "display_name": "Collab Settings",
        },
    )
    assert signup.status_code == 200, signup.text
    client.post(
        "/v1/auth/signin",
        json={"username": username, "password": "password1234"},
    )

    put0 = client.put("/v1/platform/collab-settings", json={"collab_enabled": False})
    assert put0.status_code == 200, put0.text
    assert put0.json()["collab_enabled"] is False
    assert put0.json()["source"] == "runtime"

    get0 = client.get("/v1/platform/collab-settings")
    assert get0.status_code == 200, get0.text
    assert get0.json()["collab_enabled"] is False

    put1 = client.put("/v1/platform/collab-settings", json={"collab_enabled": True})
    assert put1.status_code == 200, put1.text
    assert put1.json()["collab_enabled"] is True

    get1 = client.get("/v1/platform/collab-settings")
    assert get1.json()["collab_enabled"] is True

    from nimbusware_config.collab_settings_store import load_persisted_collab_enabled

    assert load_persisted_collab_enabled() is True

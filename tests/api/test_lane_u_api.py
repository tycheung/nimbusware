from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from nimbusware_env.admin_token import DEFAULT_NIMBUSWARE_ADMIN_TOKEN
from nimbusware_env.edition import ENTERPRISE_EDITION, ENV_EDITION
from nimbusware_iam.constants import API_KEY_HEADER
from nimbusware_iam.scopes import MAKER_ADMIN_SCOPE, MAKER_USER_SCOPE
from nimbusware_iam.store import InMemoryIamStore

ADMIN_HEADERS = {"X-Nimbusware-Admin-Token": DEFAULT_NIMBUSWARE_ADMIN_TOKEN}

pytestmark = pytest.mark.slow


def test_create_project_without_admin_token(client: TestClient, tmp_path: Path) -> None:
    ws = tmp_path / "user-project"
    ws.mkdir()
    create = client.post(
        "/v1/projects",
        json={
            "name": "User project",
            "workspace_path": str(ws),
            "template": "attach",
        },
    )
    assert create.status_code == 200
    assert create.json()["name"] == "User project"


def test_delete_project_still_requires_admin(client: TestClient, tmp_path: Path) -> None:
    ws = tmp_path / "delete-me"
    ws.mkdir()
    project_id = client.post(
        "/v1/projects",
        json={
            "name": "Delete me",
            "workspace_path": str(ws),
            "template": "attach",
        },
    ).json()["project_id"]

    denied = client.delete(f"/v1/projects/{project_id}")
    assert denied.status_code == 401

    ok = client.delete(f"/v1/projects/{project_id}", headers=ADMIN_HEADERS)
    assert ok.status_code == 204


def test_enterprise_user_key_creates_project(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv(ENV_EDITION, ENTERPRISE_EDITION)
    monkeypatch.setenv("NIMBUSWARE_ADMIN_TOKEN", "test-admin-secret")
    monkeypatch.delenv("NIMBUSWARE_DATABASE_URL", raising=False)

    iam = InMemoryIamStore()
    tenant = iam.create_tenant(slug="acme", display_name="Acme")
    user_key = iam.create_api_key(
        tenant_id=tenant.tenant_id,
        label="maker-user",
        api_scopes=[MAKER_USER_SCOPE],
    )
    admin_key = iam.create_api_key(
        tenant_id=tenant.tenant_id,
        label="maker-admin",
        api_scopes=[MAKER_USER_SCOPE, MAKER_ADMIN_SCOPE],
    )

    monkeypatch.setattr("nimbusware_iam.store.build_iam_store", lambda _url: iam)
    import importlib

    api_module = importlib.import_module("nimbusware_api.app")
    monkeypatch.setattr(api_module, "build_iam_store", lambda _url: iam)

    ws = tmp_path / "ent-user"
    ws.mkdir()

    with TestClient(api_module.app) as client:
        create = client.post(
            "/v1/projects",
            headers={API_KEY_HEADER: user_key.api_key},
            json={"name": "Tenant A", "workspace_path": str(ws), "template": "attach"},
        )
        assert create.status_code == 200
        project_id = create.json()["project_id"]

        other_ws = tmp_path / "other"
        other_ws.mkdir()
        tenant_b = iam.create_tenant(slug="other", display_name="Other")
        project_b = iam.create_api_key(
            tenant_id=tenant_b.tenant_id,
            api_scopes=[MAKER_USER_SCOPE],
        )
        client.post(
            "/v1/projects",
            headers={API_KEY_HEADER: project_b.api_key},
            json={"name": "Other", "workspace_path": str(other_ws), "template": "attach"},
        )

        listing = client.get("/v1/projects", headers={API_KEY_HEADER: user_key.api_key})
        assert listing.status_code == 200
        names = {p["name"] for p in listing.json()["projects"]}
        assert "Tenant A" in names
        assert "Other" not in names

        delete_denied = client.delete(
            f"/v1/projects/{project_id}",
            headers={API_KEY_HEADER: user_key.api_key},
        )
        assert delete_denied.status_code == 403

        delete_ok = client.delete(
            f"/v1/projects/{project_id}",
            headers={API_KEY_HEADER: admin_key.api_key},
        )
        assert delete_ok.status_code == 204

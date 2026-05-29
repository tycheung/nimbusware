"""Bundle catalog write API (§14 #12 catalog edit path)."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import yaml
from fastapi.testclient import TestClient

os.environ.setdefault("HERMES_SKIP_PREFLIGHT", "1")
os.environ.setdefault("HERMES_ADMIN_TOKEN", "test-admin-token")

from hermes_api.app import app  # noqa: E402

ADMIN_HEADERS = {"X-Hermes-Admin-Token": "test-admin-token"}
ROOT = Path(__file__).resolve().parents[1]


def test_get_and_patch_bundle_catalog(tmp_path: Path, monkeypatch) -> None:
    shutil.copytree(ROOT / "configs", tmp_path / "configs", dirs_exist_ok=True)
    bundles_dir = tmp_path / "configs" / "bundles"
    catalog = {
        "version": 1,
        "workflow_bundle_map": {"default": "auth-rbac-starter"},
        "bundles": [
            {"id": "auth-rbac-starter", "title": "Auth", "tags": ["auth"]},
        ],
    }
    (bundles_dir / "catalog.yaml").write_text(
        yaml.safe_dump(catalog, sort_keys=False),
        encoding="utf-8",
    )
    monkeypatch.setenv("HERMES_REPO_ROOT", str(tmp_path))

    with TestClient(app) as client:
        got = client.get("/v1/bundles/catalog")
        assert got.status_code == 200
        body = got.json()
        assert body["bundles"][0]["id"] == "auth-rbac-starter"

        patched = client.patch(
            "/v1/bundles/catalog/bundles/auth-rbac-starter",
            headers=ADMIN_HEADERS,
            json={"title": "Auth updated", "tags": ["auth", "rbac"]},
        )
        assert patched.status_code == 200
        assert patched.json()["bundles"][0]["title"] == "Auth updated"

    on_disk = yaml.safe_load((bundles_dir / "catalog.yaml").read_text(encoding="utf-8"))
    assert on_disk["bundles"][0]["title"] == "Auth updated"

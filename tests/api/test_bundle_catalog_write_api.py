"""Bundle catalog write API."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

import yaml
from fastapi.testclient import TestClient

from nimbusware_env import find_repo_root

os.environ.setdefault("NIMBUSWARE_SKIP_PREFLIGHT", "1")
os.environ.setdefault(
    "NIMBUSWARE_ADMIN_TOKEN", "nimbusware-dev-admin-token-SEARCH_AND_REPLACE_BEFORE_PROD"
)

from nimbusware_api.app import app  # noqa: E402

ADMIN_HEADERS = {
    "X-Nimbusware-Admin-Token": "nimbusware-dev-admin-token-SEARCH_AND_REPLACE_BEFORE_PROD"
}
ROOT = find_repo_root(start=Path(__file__).resolve().parents[1])


def _seed_catalog(tmp_path: Path) -> dict:
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
    return catalog


def test_get_and_patch_bundle_catalog(tmp_path: Path, monkeypatch) -> None:
    shutil.copytree(ROOT / "configs", tmp_path / "configs", dirs_exist_ok=True)
    _seed_catalog(tmp_path)
    monkeypatch.setenv("NIMBUSWARE_REPO_ROOT", str(tmp_path))

    with TestClient(app) as client:
        got = client.get("/v1/bundles/catalog")
        assert got.status_code == 200
        body = got.json()
        assert body["bundles"][0]["id"] == "auth-rbac-starter"
        assert body["document_version"] == 1

        patched = client.patch(
            "/v1/bundles/catalog/bundles/auth-rbac-starter",
            headers=ADMIN_HEADERS,
            json={
                "expected_version": 1,
                "title": "Auth updated",
                "tags": ["auth", "rbac"],
            },
        )
        assert patched.status_code == 200
        assert patched.json()["bundles"][0]["title"] == "Auth updated"
        assert patched.json()["document_version"] == 2

    on_disk = yaml.safe_load(
        (tmp_path / "configs" / "bundles" / "catalog.yaml").read_text(encoding="utf-8")
    )
    assert on_disk["bundles"][0]["title"] == "Auth updated"
    assert on_disk["version"] == 2


def test_post_and_delete_bundle_catalog(tmp_path: Path, monkeypatch) -> None:
    shutil.copytree(ROOT / "configs", tmp_path / "configs", dirs_exist_ok=True)
    _seed_catalog(tmp_path)
    monkeypatch.setenv("NIMBUSWARE_REPO_ROOT", str(tmp_path))

    with TestClient(app) as client:
        created = client.post(
            "/v1/bundles/catalog/bundles",
            headers=ADMIN_HEADERS,
            json={
                "expected_version": 1,
                "entry": {"id": "billing-stripe", "title": "Billing", "tags": ["billing"]},
            },
        )
        assert created.status_code == 200
        assert any(b["id"] == "billing-stripe" for b in created.json()["bundles"])
        ver = created.json()["document_version"]

        deleted = client.delete(
            "/v1/bundles/catalog/bundles/billing-stripe",
            headers=ADMIN_HEADERS,
            params={"expected_version": ver},
        )
        assert deleted.status_code == 200
        assert all(b["id"] != "billing-stripe" for b in deleted.json()["bundles"])


def test_bundle_catalog_version_conflict(tmp_path: Path, monkeypatch) -> None:
    shutil.copytree(ROOT / "configs", tmp_path / "configs", dirs_exist_ok=True)
    _seed_catalog(tmp_path)
    monkeypatch.setenv("NIMBUSWARE_REPO_ROOT", str(tmp_path))

    with TestClient(app) as client:
        r = client.patch(
            "/v1/bundles/catalog/bundles/auth-rbac-starter",
            headers=ADMIN_HEADERS,
            json={"expected_version": 99, "title": "Stale"},
        )
        assert r.status_code == 409


def test_promote_catalog_candidate(tmp_path: Path, monkeypatch) -> None:
    shutil.copytree(ROOT / "configs", tmp_path / "configs", dirs_exist_ok=True)
    _seed_catalog(tmp_path)
    monkeypatch.setenv("NIMBUSWARE_REPO_ROOT", str(tmp_path))

    cand_dir = tmp_path / ".nimbusware" / "research" / "catalog_candidates" / "run-1"
    cand_dir.mkdir(parents=True)
    payload = {
        "run_id": "run-1",
        "candidate_id": "oss-auth-kit",
        "status": "pending_integrator_review",
        "title": "OSS Auth Kit",
        "tags": ["auth", "oss"],
    }
    (cand_dir / "oss-auth-kit.json").write_text(json.dumps(payload), encoding="utf-8")

    with TestClient(app) as client:
        promoted = client.post(
            "/v1/bundles/catalog-candidates/run-1/oss-auth-kit/promote",
            headers=ADMIN_HEADERS,
            params={"expected_version": 1},
        )
        assert promoted.status_code == 200
        assert any(b["id"] == "oss-auth-kit" for b in promoted.json()["bundles"])

    marked = json.loads((cand_dir / "oss-auth-kit.json").read_text(encoding="utf-8"))
    assert marked["status"] == "promoted"


def test_promote_pending_stitch_catalog_candidates(tmp_path: Path, monkeypatch) -> None:
    shutil.copytree(ROOT / "configs", tmp_path / "configs", dirs_exist_ok=True)
    _seed_catalog(tmp_path)
    monkeypatch.setenv("NIMBUSWARE_REPO_ROOT", str(tmp_path))

    cand_dir = tmp_path / ".nimbusware" / "research" / "catalog_candidates" / "run-stitch"
    cand_dir.mkdir(parents=True)
    payload = {
        "run_id": "run-stitch",
        "candidate_id": "stitch-auth-kit",
        "status": "pending_integrator_review",
        "source": "stitch_applied",
        "title": "Stitch Auth Kit",
        "tags": ["auth", "stitch"],
    }
    (cand_dir / "stitch-auth-kit.json").write_text(json.dumps(payload), encoding="utf-8")

    with TestClient(app) as client:
        promoted = client.post(
            "/v1/bundles/catalog-candidates/promote-stitch-pending",
            headers=ADMIN_HEADERS,
            params={"expected_version": 1},
        )
        assert promoted.status_code == 200
        assert any(b["id"] == "stitch-auth-kit" for b in promoted.json()["bundles"])

    marked = json.loads((cand_dir / "stitch-auth-kit.json").read_text(encoding="utf-8"))
    assert marked["status"] == "promoted"

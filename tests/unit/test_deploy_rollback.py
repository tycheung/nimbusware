from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from api.app import app
from maker.deploy_pipeline_events import (
    deploy_rollback_passed_from_events,
    emit_deploy_rollback_stages,
)
from maker.terraform_validate import rollback_workspace_terraform
from store.memory import InMemoryEventStore


def test_rollback_skips_without_tf_files(tmp_path) -> None:
    result = rollback_workspace_terraform(tmp_path)
    assert result["status"] == "skipped"


def test_rollback_previous_skips_without_snapshot(tmp_path) -> None:
    infra = tmp_path / "infra"
    infra.mkdir()
    (infra / "main.tf").write_text('resource "null_resource" "x" {}', encoding="utf-8")
    result = rollback_workspace_terraform(infra, mode="previous")
    assert result["status"] == "skipped"
    assert "snapshot" in result["detail"]


def test_deploy_rollback_events() -> None:
    store = InMemoryEventStore()
    rid = uuid4()
    emit_deploy_rollback_stages(
        store,
        rid,
        {"status": "passed", "detail": "ok", "rollback_mode": "destroy"},
    )
    rows = store.list_run_events(str(rid))
    assert deploy_rollback_passed_from_events(rows) is True


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


def test_deploy_rollback_requires_apply(client: TestClient) -> None:
    created = client.post("/v1/runs", json={"workflow_profile": "default"})
    run_id = created.json()["run_id"]
    resp = client.post(
        "/v1/platform/deploy/rollback",
        json={"run_id": run_id, "workspace_path": "infra"},
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "deploy_apply_required"


def test_deploy_rollback_after_apply(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    created = client.post("/v1/runs", json={"workflow_profile": "default"})
    run_id = created.json()["run_id"]
    client.post("/v1/platform/deploy/approve", json={"run_id": run_id})
    monkeypatch.setattr(
        "api.routes.platform_deploy_mutations.maker_user_id_str",
        lambda _req: "deploy-test-user",
    )
    monkeypatch.setattr(
        "api.routes.platform_deploy_mutations.load_deploy_credentials",
        lambda *_a, **_k: {"aws_profile": "dev"},
    )
    monkeypatch.setattr(
        "api.routes.platform_deploy_mutations.apply_workspace_terraform",
        lambda _ws, **_: {"status": "passed", "detail": "ok"},
    )
    monkeypatch.setattr(
        "api.routes.platform_deploy_mutations.rollback_workspace_terraform",
        lambda _ws, **_: {"status": "passed", "detail": "destroy ok", "rollback_mode": "destroy"},
    )
    client.post(
        "/v1/platform/deploy/apply",
        json={"run_id": run_id, "workspace_path": "infra"},
    )
    resp = client.post(
        "/v1/platform/deploy/rollback",
        json={"run_id": run_id, "workspace_path": "infra", "mode": "destroy"},
    )
    assert resp.status_code == 200, resp.text
    timeline = client.get(f"/v1/runs/{run_id}/timeline?limit=80")
    events = timeline.json().get("events") or []
    assert any(ev.get("payload", {}).get("stage_name") == "deploy.rollback" for ev in events)

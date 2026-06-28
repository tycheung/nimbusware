from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from nimbusware_api.app import app
from nimbusware_maker.deploy_pipeline_events import (
    deploy_apply_passed_from_events,
    emit_deploy_apply_stages,
    live_urls_from_events,
)
from nimbusware_maker.deploy_smoke import run_deploy_smoke
from nimbusware_store.memory import InMemoryEventStore


def test_run_deploy_smoke_skips_without_urls() -> None:
    result = run_deploy_smoke()
    assert result["status"] == "skipped"


def test_run_deploy_smoke_http_pass(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeResp:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *_a):
            return False

    monkeypatch.setattr(
        "nimbusware_maker.deploy_smoke.urlopen",
        lambda *_a, **_k: FakeResp(),
    )
    result = run_deploy_smoke(api_url="https://api.example.com", web_url="https://app.example.com")
    assert result["status"] == "passed"
    assert len(result["checks"]) == 2


def test_live_urls_from_apply_event() -> None:
    store = InMemoryEventStore()
    rid = uuid4()
    emit_deploy_apply_stages(
        store,
        rid,
        {
            "status": "passed",
            "detail": "ok",
            "api_url": "https://api.test",
            "web_url": "https://web.test",
        },
    )
    rows = store.list_run_events(str(rid))
    assert live_urls_from_events(rows) == {
        "api_url": "https://api.test",
        "web_url": "https://web.test",
    }
    assert deploy_apply_passed_from_events(rows) is True


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


def test_deploy_smoke_requires_apply(client: TestClient) -> None:
    created = client.post("/v1/runs", json={"workflow_profile": "default"})
    run_id = created.json()["run_id"]
    resp = client.post("/v1/platform/deploy/smoke", json={"run_id": run_id})
    assert resp.status_code == 403
    assert resp.json()["code"] == "deploy_apply_required"


def test_deploy_smoke_after_apply(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    created = client.post("/v1/runs", json={"workflow_profile": "default"})
    run_id = created.json()["run_id"]
    approve = client.post("/v1/platform/deploy/approve", json={"run_id": run_id})
    assert approve.status_code == 200
    monkeypatch.setattr(
        "nimbusware_api.routes.platform_deploy.maker_user_id_str",
        lambda _req: "deploy-test-user",
    )
    monkeypatch.setattr(
        "nimbusware_api.routes.platform_deploy.load_deploy_credentials",
        lambda *_a, **_k: {"aws_profile": "dev"},
    )
    monkeypatch.setattr(
        "nimbusware_api.routes.platform_deploy.apply_workspace_terraform",
        lambda _ws, **_: {
            "status": "passed",
            "detail": "ok",
            "api_url": "https://api.test",
        },
    )
    monkeypatch.setattr(
        "nimbusware_api.routes.platform_deploy.run_deploy_smoke",
        lambda **_: {"status": "passed", "detail": "1/1 checks passed", "checks": []},
    )
    apply = client.post(
        "/v1/platform/deploy/apply",
        json={"run_id": run_id, "workspace_path": "infra"},
    )
    assert apply.status_code == 200, apply.text
    body = apply.json()
    assert body.get("smoke", {}).get("status") == "passed", body
    timeline = client.get(f"/v1/runs/{run_id}/timeline?limit=50")
    events = timeline.json().get("events") or []
    smoke_stages = [
        ev for ev in events if ev.get("payload", {}).get("stage_name") == "deploy.smoke"
    ]
    assert smoke_stages

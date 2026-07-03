from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from agent_core.models import EventType, RunCreatedEvent
from agent_core.models.events_payloads import RunCreatedPayload
from api.app import app
from maker.deploy_pipeline_events import (
    autopilot_may_auto_approve_deploy,
    deploy_approved_from_events,
    emit_deploy_approved,
)
from store.memory import InMemoryEventStore


def _seed_run() -> tuple[InMemoryEventStore, str]:
    store = InMemoryEventStore()
    rid = uuid4()
    store.append(
        RunCreatedEvent(
            event_type=EventType.RUN_CREATED,
            event_id=uuid4(),
            run_id=rid,
            occurred_at=datetime.now(timezone.utc),
            payload=RunCreatedPayload(
                workflow_profile="campaign_fullstack",
                policy_version="1",
                config_snapshot_id=str(uuid4()),
            ),
        ),
    )
    return store, str(rid)


def test_deploy_approved_from_events_false_until_emitted() -> None:
    store, rid = _seed_run()
    rows = store.list_run_events(rid)
    assert deploy_approved_from_events(rows) is False
    emit_deploy_approved(store, rid)
    assert deploy_approved_from_events(store.list_run_events(rid)) is True


def test_autopilot_deploy_profile_gate() -> None:
    assert autopilot_may_auto_approve_deploy({"level": 9, "checkpoints": []}) is True
    assert (
        autopilot_may_auto_approve_deploy(
            {"level": 5, "checkpoints": ["stop_before_deploy_apply"]},
        )
        is False
    )


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


def test_deploy_apply_requires_approval(client: TestClient) -> None:
    created = client.post("/v1/runs", json={"workflow_profile": "default"})
    assert created.status_code == 200, created.text
    run_id = created.json()["run_id"]
    resp = client.post(
        "/v1/platform/deploy/apply",
        json={"run_id": run_id, "workspace_path": "infra"},
    )
    assert resp.status_code == 403, resp.text
    assert resp.json()["code"] == "deploy_approval_required"


def test_deploy_apply_skips_without_credentials(client: TestClient, monkeypatch, tmp_path) -> None:
    created = client.post("/v1/runs", json={"workflow_profile": "default"})
    run_id = created.json()["run_id"]
    approve = client.post("/v1/platform/deploy/approve", json={"run_id": run_id})
    assert approve.status_code == 200, approve.text
    monkeypatch.setattr(
        "api.routes.platform_deploy_mutations.load_deploy_credentials",
        lambda *_a, **_k: {"aws_profile": "", "github_repo": ""},
    )
    ws = tmp_path / "infra"
    ws.mkdir()
    resp = client.post(
        "/v1/platform/deploy/apply",
        json={"run_id": run_id, "workspace_path": str(ws)},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "skipped"
    timeline = client.get(f"/v1/runs/{run_id}/timeline?limit=50")
    events = timeline.json().get("events") or []
    assert any(ev.get("payload", {}).get("stage_name") == "deploy.apply" for ev in events)


def test_deploy_apply_denied_when_target_not_allowed(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    policy_path = tmp_path / "configs" / "enterprise" / "fleet_deploy_policies.yaml"
    policy_path.parent.mkdir(parents=True)
    policy_path.write_text(
        "version: 1\ntenants:\n  default:\n    allowed_deploy_targets:\n      - github-actions\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("NIMBUSWARE_SETUP_BUNDLE", "enterprise")
    monkeypatch.setattr(
        "orchestrator.fleet_policy_loader.find_repo_root",
        lambda *_a, **_k: tmp_path,
    )
    monkeypatch.setattr(
        "api.routes.platform_deploy_mutations.load_deploy_credentials",
        lambda *_a, **_k: {"aws_profile": "prod", "github_repo": ""},
    )

    created = client.post(
        "/v1/runs",
        json={
            "workflow_profile": "campaign_fullstack",
            "requirements": {
                "business_prompt": "Deploy todo app",
                "stack_manifest": {
                    "surfaces": ["deploy"],
                    "stacks": {"deploy": "terraform_aws_ecs"},
                    "confirmed": True,
                },
            },
        },
    )
    assert created.status_code == 200, created.text
    run_id = created.json()["run_id"]
    approve = client.post("/v1/platform/deploy/approve", json={"run_id": run_id})
    assert approve.status_code == 200, approve.text
    resp = client.post(
        "/v1/platform/deploy/apply",
        json={"run_id": run_id, "workspace_path": str(tmp_path / "infra")},
    )
    assert resp.status_code == 403, resp.text
    assert resp.json()["code"] == "deploy_target_denied"

"""Admin UI BFF: operator chat and formatted tables."""

from __future__ import annotations

import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("NIMBUSWARE_SKIP_PREFLIGHT", "1")

from nimbusware_api.app import app  # noqa: E402
from nimbusware_console.services import enterprise as enterprise_svc  # noqa: E402
from nimbusware_env.admin_token import DEFAULT_NIMBUSWARE_ADMIN_TOKEN

ADMIN_HEADERS = {
    "X-Nimbusware-Admin-Token": os.environ.get(
        "NIMBUSWARE_ADMIN_TOKEN",
        DEFAULT_NIMBUSWARE_ADMIN_TOKEN,
    ),
}


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


def test_operator_chat_help(client: TestClient) -> None:
    headers = {
        **ADMIN_HEADERS,
        "X-Nimbusware-Chat-Session": "test-session",
    }
    r = client.post(
        "/v1/admin/ui/operator-chat/message",
        json={"text": "/help"},
        headers=headers,
    )
    assert r.status_code == 200
    assert "Commands" in r.json()["reply"]


def test_findings_table_not_found(client: TestClient) -> None:
    rid = str(uuid4())
    r = client.get(
        f"/v1/admin/ui/runs/{rid}/findings-table",
        headers=ADMIN_HEADERS,
    )
    assert r.status_code == 404


def test_fleet_dashboard_individual_edition_404(client: TestClient) -> None:
    from nimbusware_iam.constants import API_KEY_HEADER

    r = client.get(
        "/v1/admin/ui/enterprise/fleet-dashboard",
        headers={**ADMIN_HEADERS, API_KEY_HEADER: "any-key"},
    )
    assert r.status_code == 404


def test_fleet_dashboard_missing_api_key_401(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from nimbusware_env.edition import ENTERPRISE_EDITION, ENV_EDITION

    monkeypatch.setenv(ENV_EDITION, ENTERPRISE_EDITION)
    r = client.get(
        "/v1/admin/ui/enterprise/fleet-dashboard",
        headers=ADMIN_HEADERS,
    )
    assert r.status_code == 401


def test_fleet_dashboard_enterprise_formatted(monkeypatch: pytest.MonkeyPatch) -> None:
    import importlib

    from nimbusware_env.edition import ENTERPRISE_EDITION, ENV_EDITION
    from nimbusware_iam.constants import API_KEY_HEADER
    from nimbusware_iam.scopes import MAKER_ADMIN_SCOPE
    from nimbusware_iam.store import InMemoryIamStore

    monkeypatch.setenv(ENV_EDITION, ENTERPRISE_EDITION)
    monkeypatch.delenv("NIMBUSWARE_DATABASE_URL", raising=False)
    iam = InMemoryIamStore()
    tenant = iam.create_tenant(slug="ops", display_name="Ops")
    created = iam.create_api_key(
        tenant_id=tenant.tenant_id,
        label="fleet-admin",
        api_scopes=[MAKER_ADMIN_SCOPE],
    )
    monkeypatch.setattr("nimbusware_iam.store.build_iam_store", lambda _url: iam)
    api_module = importlib.import_module("nimbusware_api.app")
    monkeypatch.setattr(api_module, "build_iam_store", lambda _url: iam)

    memory = {"tenant_id": "t1", "local_chunk_count": 2, "remote": {"configured": True}}
    preflight = {"fleet_sli": {"sustained_export_present": False}}
    worker = {"ok": True, "backpressure": "ok", "metrics": {"queue": {"pending": 0}}}
    hardware = {"hosts": [{"host": "h1", "tier": "A", "ram_total_gb": 16}]}

    monkeypatch.setattr(
        enterprise_svc,
        "fetch_fleet_memory_status",
        lambda *, api_key, timeout=30.0: memory,
    )
    monkeypatch.setattr(
        enterprise_svc,
        "fetch_fleet_preflight_aggregate",
        lambda *, api_key, limit=10, timeout=30.0: preflight,
    )
    monkeypatch.setattr(
        enterprise_svc,
        "fetch_fleet_worker_health",
        lambda *, api_key, timeout=30.0: worker,
    )
    monkeypatch.setattr(
        enterprise_svc,
        "fetch_platform_hardware_fleet",
        lambda *, timeout=30.0: hardware,
    )

    with TestClient(api_module.app) as client:
        r = client.get(
            "/v1/admin/ui/enterprise/fleet-dashboard",
            headers={**ADMIN_HEADERS, API_KEY_HEADER: created.api_key},
        )
    assert r.status_code == 200
    body = r.json()
    assert body["export_filename_slug"] == "enterprise_fleet_dashboard"
    assert any(row["field"] == "local_chunk_count" for row in body["memory_rows"])
    assert len(body["hardware_rows"]) == 1
    assert "Fleet worker" in (body["worker_caption"] or "")


def test_integration_adapter_writer_bff_present() -> None:
    from datetime import datetime, timezone

    from agent_core.models import EventType, StageStartedEvent, StageStartedPayload
    from nimbusware_store.memory import InMemoryEventStore

    store = InMemoryEventStore()
    rid = uuid4()
    store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=uuid4(),
            run_id=rid,
            occurred_at=datetime.now(timezone.utc),
            metadata={
                "integration_adapter_writer": {
                    "scaffold_status": "target_integrated",
                    "target_integration_status": "integrated",
                    "target_adapter_kind": "api_bridge",
                    "workspace_manifest_path": ".nimbusware/integration_adapter_writer/x/manifest.json",
                },
            },
            payload=StageStartedPayload(
                stage_name="integration_adapter_writer",
                attempt=1,
            ),
        ),
    )
    with TestClient(app) as client:
        client.app.state.store = store
        client.app.state.orchestrator.store = store
        r = client.get(
            f"/v1/admin/ui/runs/{rid}/integration-adapter-writer",
            headers=ADMIN_HEADERS,
        )
    assert r.status_code == 200
    body = r.json()
    assert body["present"] is True
    assert body["caption"]
    assert any(row["field"] == "Target integration" for row in body["rows"])


def test_integration_adapter_writer_bff_not_found(client: TestClient) -> None:
    rid = str(uuid4())
    r = client.get(
        f"/v1/admin/ui/runs/{rid}/integration-adapter-writer",
        headers=ADMIN_HEADERS,
    )
    assert r.status_code == 404


def test_critic_reliability_table_not_found(client: TestClient) -> None:
    rid = str(uuid4())
    r = client.get(
        f"/v1/admin/ui/runs/{rid}/critic-reliability",
        headers=ADMIN_HEADERS,
    )
    assert r.status_code == 404


def test_fleet_dashboard_critic_reliability_formatted(monkeypatch: pytest.MonkeyPatch) -> None:
    import importlib

    from nimbusware_env.edition import ENTERPRISE_EDITION, ENV_EDITION
    from nimbusware_iam.constants import API_KEY_HEADER
    from nimbusware_iam.scopes import MAKER_ADMIN_SCOPE
    from nimbusware_iam.store import InMemoryIamStore

    monkeypatch.setenv(ENV_EDITION, ENTERPRISE_EDITION)
    monkeypatch.delenv("NIMBUSWARE_DATABASE_URL", raising=False)
    iam = InMemoryIamStore()
    tenant = iam.create_tenant(slug="ops", display_name="Ops")
    created = iam.create_api_key(
        tenant_id=tenant.tenant_id,
        label="fleet-admin",
        api_scopes=[MAKER_ADMIN_SCOPE],
    )
    monkeypatch.setattr("nimbusware_iam.store.build_iam_store", lambda _url: iam)
    api_module = importlib.import_module("nimbusware_api.app")
    monkeypatch.setattr(api_module, "build_iam_store", lambda _url: iam)

    critic = {
        "tenant_id": str(tenant.tenant_id),
        "runs_scanned": 2,
        "runs_with_critics": 1,
        "critic_verdict_count": 4,
        "critic_fail_count": 1,
        "critic_fail_rate": 0.25,
        "out_of_domain_verdict_count": 1,
        "out_of_domain_rate": 0.25,
        "gate_block_count": 0,
        "repeat_finding_paths": 0,
    }

    monkeypatch.setattr(
        enterprise_svc,
        "fetch_fleet_memory_status",
        lambda *, api_key, timeout=30.0: {},
    )
    monkeypatch.setattr(
        enterprise_svc,
        "fetch_fleet_preflight_aggregate",
        lambda *, api_key, limit=10, timeout=30.0: {},
    )
    monkeypatch.setattr(
        enterprise_svc,
        "fetch_fleet_worker_health",
        lambda *, api_key, timeout=30.0: {},
    )
    monkeypatch.setattr(
        enterprise_svc,
        "fetch_platform_hardware_fleet",
        lambda *, timeout=30.0: {"hosts": []},
    )
    monkeypatch.setattr(
        enterprise_svc,
        "fetch_fleet_critic_reliability",
        lambda *, api_key, tenant_id, run_limit=100, timeout=30.0: critic,
    )

    with TestClient(api_module.app) as client:
        r = client.get(
            "/v1/admin/ui/enterprise/fleet-dashboard",
            headers={**ADMIN_HEADERS, API_KEY_HEADER: created.api_key},
            params={"tenant_id": "ops"},
        )
    assert r.status_code == 200
    body = r.json()
    assert body["critic_reliability_caption"]
    assert any(row["metric"] == "Runs scanned" for row in body["critic_reliability_rows"])

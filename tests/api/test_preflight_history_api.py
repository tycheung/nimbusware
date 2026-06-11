from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from nimbusware_env import find_repo_root

os.environ.setdefault(
    "NIMBUSWARE_REPO_ROOT", str(find_repo_root(start=Path(__file__).resolve().parents[1]))
)
os.environ.setdefault("NIMBUSWARE_SKIP_PREFLIGHT", "1")
os.environ.setdefault(
    "NIMBUSWARE_ADMIN_TOKEN", "nimbusware-dev-admin-token-SEARCH_AND_REPLACE_BEFORE_PROD"
)

from agent_core.models import (  # noqa: E402
    EventType,
    ModelPreflightPassedEvent,
    ModelPreflightPassedPayload,
)
from nimbusware_api.app import app  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


def test_preflight_history_empty(client: TestClient) -> None:
    r = client.get("/v1/preflight-history", params={"limit": 5})
    assert r.status_code == 200
    body = r.json()
    if body["total"] > 0 and os.environ.get("NIMBUSWARE_DATABASE_URL"):
        pytest.skip(
            "event_store has prior runs on this Postgres URL; use a fresh DB for empty-state test",
        )
    assert body["entries"] == []
    assert body["total"] == 0
    assert body["has_more"] is False
    assert body["limit"] == 5


def test_preflight_history_with_and_without_preflight(client: TestClient) -> None:
    r1 = client.post("/v1/runs", json={"workflow_profile": "default"})
    run_with = UUID(r1.json()["run_id"])
    r2 = client.post("/v1/runs", json={"workflow_profile": "default"})
    run_without = UUID(r2.json()["run_id"])
    store = client.app.state.store
    store.append(
        ModelPreflightPassedEvent(
            event_type=EventType.MODEL_PREFLIGHT_PASSED,
            event_id=uuid4(),
            run_id=run_with,
            occurred_at=datetime.now(timezone.utc),
            payload=ModelPreflightPassedPayload(
                provider="ollama",
                validated_model_id="m1",
                context_tokens=4096,
                p95_latency_ms=99,
                checks_passed=["runtime_reachable"],
                health_latency_samples_ms=[90, 95, 99],
            ),
        ),
    )
    resp = client.get("/v1/preflight-history", params={"limit": 10, "order": "newest_first"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 2
    by_id = {e["run_id"]: e["preflight"] for e in body["entries"]}
    assert str(run_with) in by_id
    assert by_id[str(run_with)] is not None
    assert by_id[str(run_with)]["p95_latency_ms"] == 99
    assert str(run_without) in by_id
    assert by_id[str(run_without)] is None
    assert body["runs_with_preflight"] >= 1
    assert body["runs_without_preflight"] >= 1
    assert body["runs_with_p95_latency"] >= 1
    assert body["avg_p95_latency_ms"] is not None
    assert body["max_p95_latency_ms"] is not None
    assert 0.0 <= float(body["preflight_coverage_ratio"]) <= 1.0
    if body["runs_with_preflight"] > 0:
        assert body["p95_latency_coverage_ratio"] is not None
        assert 0.0 <= float(body["p95_latency_coverage_ratio"]) <= 1.0
    assert body["runs_with_multisample_preflight"] >= 1
    assert body["runs_with_checks_passed"] >= 1
    assert body["distinct_validated_model_id_count"] >= 1


def test_preflight_history_limit_cap(client: TestClient) -> None:
    for _ in range(3):
        client.post("/v1/runs", json={"workflow_profile": "default"})
    r = client.get("/v1/preflight-history", params={"limit": 2})
    assert r.status_code == 200
    assert len(r.json()["entries"]) == 2
    assert r.json()["limit"] == 2


def test_preflight_history_limit_over_max_422(client: TestClient) -> None:
    r = client.get("/v1/preflight-history", params={"limit": 51})
    assert r.status_code == 422


def test_preflight_history_metrics_export_payload(client: TestClient) -> None:
    client.post("/v1/runs", json={"workflow_profile": "default"})
    r = client.get(
        "/v1/preflight-history",
        params={
            "limit": 5,
            "offset": 0,
            "status": "created",
            "include_metrics_export": 1,
        },
    )
    assert r.status_code == 200
    body = r.json()
    export = body.get("metrics_export")
    assert isinstance(export, dict)
    assert export["window_limit"] == 5
    assert export["export_schema_version"] == 1
    assert export["window_total_matching_runs"] >= export["runs_scanned"]
    assert export["runs_scanned"] >= 1
    assert isinstance(export["has_more"], bool)
    assert export["export_window_consistent"] is True
    assert export["filters"]["status"] == "created"
    assert export["filters"]["workflow_profile"] is None
    assert export["filters"]["workflow_profile_prefix"] is None
    assert "generated_at" in export

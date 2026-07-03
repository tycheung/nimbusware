from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

import pytest

pytest.importorskip("pytest_benchmark")

os.environ.setdefault("NIMBUSWARE_REPO_ROOT", str(Path(__file__).resolve().parents[2]))
os.environ.setdefault("NIMBUSWARE_SKIP_PREFLIGHT", "1")

from fastapi.testclient import TestClient  # noqa: E402

from agent_core.models import (  # noqa: E402
    EventType,
    ModelPreflightPassedEvent,
    ModelPreflightPassedPayload,
)
from api.app import app  # noqa: E402
from orchestrator.fleet.benchmark import benchmark_preflight_history_scan  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


def _seed_preflight_runs(client: TestClient, count: int) -> None:
    store = client.app.state.store
    for i in range(count):
        r = client.post("/v1/runs", json={"workflow_profile": "default"})
        run_id = UUID(r.json()["run_id"])
        store.append(
            ModelPreflightPassedEvent(
                event_type=EventType.MODEL_PREFLIGHT_PASSED,
                event_id=uuid4(),
                run_id=run_id,
                occurred_at=datetime.now(timezone.utc),
                payload=ModelPreflightPassedPayload(
                    provider="ollama",
                    validated_model_id="llama3.1:8b",
                    context_tokens=8192,
                    p95_latency_ms=50 + i,
                    checks_passed=["runtime_reachable"],
                ),
            ),
        )


@pytest.mark.benchmark(group="fleet_preflight")
def test_preflight_history_http_benchmark(benchmark, client: TestClient) -> None:
    _seed_preflight_runs(client, 25)

    def _call() -> None:
        r = client.get("/v1/preflight-history", params={"limit": 25})
        assert r.status_code == 200

    benchmark(_call)


@pytest.mark.benchmark(group="fleet_preflight")
def test_preflight_history_store_scan_benchmark(benchmark, client: TestClient) -> None:
    _seed_preflight_runs(client, 25)
    store = client.app.state.store

    def _scan() -> dict:
        return benchmark_preflight_history_scan(store, limit=25)

    result = benchmark(_scan)
    assert result["runs_scanned"] == 25
    assert result["runs_with_preflight"] == 25

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from agent_core.models import (
    EventType,
    GateDecisionEmittedEvent,
    GateDecisionEmittedPayload,
    Verdict,
)
from api.app import app
from env import find_repo_root
from extensions.extension_runtime import UniversalCritiqueRouter
from orchestrator.critique_routing import (
    CRITIQUE_STAGE_TO_PRODUCER,
    critique_coverage_snapshot,
)
from orchestrator.registry import RoleRegistry


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


def test_critique_stage_to_producer_mapping_contract() -> None:
    assert CRITIQUE_STAGE_TO_PRODUCER["planner.critique"] == "planner"
    assert CRITIQUE_STAGE_TO_PRODUCER["implementation.critique"] == "backend_writer"
    assert CRITIQUE_STAGE_TO_PRODUCER["test_writer.critique"] == "test_writer"
    assert CRITIQUE_STAGE_TO_PRODUCER["frontend_writer.critique"] == "frontend_writer"
    assert CRITIQUE_STAGE_TO_PRODUCER["module_integrator.critique"] == "module_integrator"


def test_critique_coverage_snapshot_registry_has_thirteen_producers() -> None:
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    reg = RoleRegistry.from_yaml(root / "configs" / "roles.yaml")
    router = UniversalCritiqueRouter.from_yaml(
        root / "configs" / "personas" / "critique_pairings.yaml",
    )
    snap = critique_coverage_snapshot(reg, router)
    assert len(snap["registry_producers"]) == 13
    assert "infra_writer" in snap["registry_producers"]
    assert "launch_test_writer" in snap["registry_producers"]
    assert "refactorer" in snap["registry_producers"]
    assert "agent_evaluator" not in snap["registry_producers"]
    assert snap["unpaired_producers"] == []
    assert snap["pairing_errors"] == []


def test_critique_coverage_snapshot_happy_and_missing_pairing() -> None:
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    reg = RoleRegistry.from_yaml(root / "configs" / "roles.yaml")
    router_ok = UniversalCritiqueRouter.from_content(
        {
            "version": 1,
            "pairings": {
                "planner": ["product_reference_critic"],
                "backend_writer": ["product_reference_critic"],
                "test_writer": ["domain_critic"],
            },
        },
    )
    snap_ok = critique_coverage_snapshot(reg, router_ok)
    assert "planner" in snap_ok["paired_producers"]
    assert snap_ok["pairing_errors"] == []

    router_bad = UniversalCritiqueRouter.from_content(
        {
            "version": 1,
            "pairings": {
                "planner": ["nonexistent_critic_taxonomy_key"],
                "backend_writer": [],
                "test_writer": ["domain_critic"],
            },
        },
    )
    snap_bad = critique_coverage_snapshot(reg, router_bad)
    assert "backend_writer" in snap_bad["unpaired_producers"]
    assert any(e["producer"] == "planner" for e in snap_bad["pairing_errors"])


def test_create_run_freezes_critique_coverage_on_run_created(client: TestClient) -> None:
    r = client.post("/v1/runs", json={"workflow_profile": "default"})
    assert r.status_code == 200, r.text
    run_id = r.json()["run_id"]
    rows = client.app.state.store.list_run_events(run_id)
    created = next(x for x in rows if x.get("event_type") == "run.created")
    cc = (created.get("metadata") or {}).get("critique_coverage")
    assert isinstance(cc, dict)
    assert len(cc.get("registry_producers") or []) == 13
    assert "registry_producers" in cc
    assert "paired_producers" in cc
    assert "pairing_errors" in cc


def test_timeline_universal_critique_includes_producer_and_coverage(
    client: TestClient,
) -> None:
    r = client.post("/v1/runs", json={"workflow_profile": "default"})
    run_id = UUID(r.json()["run_id"])
    store = client.app.state.store
    store.append(
        GateDecisionEmittedEvent(
            event_type=EventType.GATE_DECISION_EMITTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata={},
            payload=GateDecisionEmittedPayload(
                stage_name="implementation.critique",
                verdict=Verdict.PASS,
            ),
        ),
    )
    tl = client.get(f"/v1/runs/{run_id}/timeline").json()
    uc = tl["universal_critique"]
    assert uc is not None
    assert isinstance(uc.get("critique_coverage"), dict)
    impl = next(s for s in uc["stages"] if s["stage_name"] == "implementation.critique")
    assert impl["producer_taxonomy_key"] == "backend_writer"

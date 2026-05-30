from __future__ import annotations
from nimbusware_env import find_repo_root

from pathlib import Path
from uuid import uuid4

from agent_core.models import EventType, Verdict
from hermes_extensions.bundle_memory import (
    InMemoryBundleOutcomeStore,
    aggregate_bundle_success_stats,
    build_bundle_outcome_from_gate,
    bundle_outcome_metadata,
    extract_bundle_outcomes_from_event_rows,
)
from hermes_orchestrator.pipeline import make_dev_orchestrator


def test_build_bundle_outcome_metadata() -> None:
    run_id = uuid4()
    rec = build_bundle_outcome_from_gate(
        run_id=run_id,
        bundle_id="auth-rbac-starter",
        workflow_profile="default",
        project_tags=["auth", "rbac"],
        integrator_score=0.82,
        verdict=Verdict.PASS,
    )
    meta = bundle_outcome_metadata(rec)
    assert meta["bundle_id"] == "auth-rbac-starter"
    assert meta["verdict"] == "PASS"


def test_extract_bundle_outcomes_from_gate_events() -> None:
    run_id = uuid4()
    rows = [
        {
            "store_seq": 1,
            "run_id": run_id,
            "event_type": EventType.RUN_CREATED.value,
            "payload": {"workflow_profile": "integrator_gate_on"},
        },
        {
            "store_seq": 2,
            "run_id": run_id,
            "event_type": EventType.GATE_DECISION_EMITTED.value,
            "metadata": {
                "integrator_gate": True,
                "bundle_id": "auth-rbac-starter",
                "integrator_score": 0.4,
                "integrator_project_tags": ["auth"],
                "bundle_outcome": {
                    "bundle_id": "auth-rbac-starter",
                    "workflow_profile": "integrator_gate_on",
                    "project_tags": ["auth"],
                    "integrator_score": 0.4,
                    "verdict": "FAIL",
                },
            },
            "payload": {
                "stage_name": "bundle_compatibility",
                "verdict": Verdict.FAIL.value,
            },
        },
    ]
    outcomes = extract_bundle_outcomes_from_event_rows(rows)
    assert len(outcomes) == 1
    assert outcomes[0].bundle_id == "auth-rbac-starter"
    assert outcomes[0].verdict == Verdict.FAIL.value


def test_emit_integrator_gate_persists_bundle_outcome(monkeypatch) -> None:
    monkeypatch.setenv("HERMES_EMIT_INTEGRATOR_GATE", "1")
    repo = find_repo_root(start=Path(__file__).resolve().parents[1])
    store = InMemoryBundleOutcomeStore()
    orch, _mem = make_dev_orchestrator(repo, bundle_outcome_store=store)
    run_id = orch.create_run("integrator_gate_on")
    orch._emit_bundle_integrator_gate(run_id)
    assert store.records
    assert store.records[0].bundle_id


def test_aggregate_bundle_success_stats() -> None:
    run_id = uuid4()
    store = InMemoryBundleOutcomeStore()
    store.append(
        build_bundle_outcome_from_gate(
            run_id=run_id,
            bundle_id="a",
            workflow_profile="wf",
            project_tags=[],
            integrator_score=0.9,
            verdict=Verdict.PASS,
        ),
    )
    store.append(
        build_bundle_outcome_from_gate(
            run_id=uuid4(),
            bundle_id="a",
            workflow_profile="wf",
            project_tags=[],
            integrator_score=0.2,
            verdict=Verdict.FAIL,
        ),
    )
    stats = aggregate_bundle_success_stats(store.list_all())
    assert stats["a"].pass_count == 1
    assert stats["a"].fail_count == 1
    assert stats["a"].success_rate == 0.5

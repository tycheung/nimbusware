from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from agent_core.models import (  # noqa: E402
    EventType,
    FindingCreatedEvent,
    FindingCreatedPayload,
    GateDecisionEmittedEvent,
    GateDecisionEmittedPayload,
    ModelPreflightPassedEvent,
    ModelPreflightPassedPayload,
    RunEscalatedEvent,
    RunEscalatedPayload,
    SelfRefinementLoopSignalledEvent,
    SelfRefinementLoopSignalledPayload,
    Severity,
    StageFailedEvent,
    StageFailedPayload,
    StagePassedEvent,
    StagePassedPayload,
    StageStartedEvent,
    StageStartedPayload,
    Verdict,
)

pytestmark = pytest.mark.slow

def test_create_run_and_timeline(client: TestClient) -> None:
    r = client.post("/v1/runs", json={"workflow_profile": "default"})
    assert r.status_code == 200
    run_id = r.json()["run_id"]
    t = client.get(f"/v1/runs/{run_id}/timeline")
    assert t.status_code == 200
    body = t.json()
    assert len(body["events"]) == 1
    assert "integrator_gate" in body
    assert body["integrator_gate"] is None
    assert body.get("integrator_gate_history") is None
    assert body.get("integrator_gate_delta") is None
    assert "agent_evaluator" in body
    assert body["agent_evaluator"] is None
    assert "self_refinement" in body
    assert body["self_refinement"] is None
    assert "run_escalated" in body
    assert body["run_escalated"] is None
    assert body.get("run_escalated_history") is None
    assert body.get("run_escalated_delta") is None
    assert "security_scan_on_verify" in body
    assert body["security_scan_on_verify"] is None
    assert body.get("security_scan_on_verify_history") is None
    assert body.get("self_refinement_marker_history") is None
    assert "scraper_fetch" in body
    assert body["scraper_fetch"] is None
    assert "universal_critique" in body
    assert body["universal_critique"] is None
    assert "stage_graph" in body
    sg = body.get("stage_graph")
    assert isinstance(sg, dict)
    assert sg.get("stage_count", 0) >= 1
    assert "persona_assignment" in body
    assert body["persona_assignment"] is None


def test_timeline_integrator_gate_summary_from_bundle_gate_events(client: TestClient) -> None:
    r = client.post("/v1/runs", json={"workflow_profile": "default"})
    run_id = UUID(r.json()["run_id"])
    eid = uuid4()
    store = client.app.state.store
    store.append(
        GateDecisionEmittedEvent(
            event_type=EventType.GATE_DECISION_EMITTED,
            event_id=eid,
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata={
                "integrator_gate": True,
                "bundle_id": "auth-rbac-starter",
                "bundle_title": "Admin RBAC starter",
                "integrator_score": 0.9,
                "min_score_to_pass": 0.3,
                "integrator_project_tags": ["auth-rbac-starter"],
                "integrator_bundle_tags": ["auth"],
                "integrator_matched_tags": ["auth"],
            },
            payload=GateDecisionEmittedPayload(
                stage_name="bundle_compatibility",
                verdict=Verdict.PASS,
                unanimous_pass_required=False,
            ),
        ),
    )
    tl = client.get(f"/v1/runs/{run_id}/timeline").json()
    ig = tl["integrator_gate"]
    assert ig is not None
    assert ig["event_id"] == str(eid)
    assert ig["stage_name"] == "bundle_compatibility"
    assert ig["verdict"] == "PASS"
    assert ig["failure_reason_code"] is None
    assert ig["bundle_id"] == "auth-rbac-starter"
    assert ig["integrator_score"] == pytest.approx(0.9)


def test_timeline_integrator_gate_bundle_compatibility_ranking(client: TestClient) -> None:
    r = client.post("/v1/runs", json={"workflow_profile": "default"})
    run_id = UUID(r.json()["run_id"])
    eid = uuid4()
    store = client.app.state.store
    ranking = [
        {"bundle_id": "top", "score": 0.95, "passes_gate": True, "title": "Top"},
        {"bundle_id": "auth-rbac-starter", "score": 0.9, "passes_gate": True},
    ]
    store.append(
        GateDecisionEmittedEvent(
            event_type=EventType.GATE_DECISION_EMITTED,
            event_id=eid,
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata={
                "integrator_gate": True,
                "bundle_id": "auth-rbac-starter",
                "integrator_score": 0.9,
                "bundle_compatibility_ranking": ranking,
                "bundle_compatibility_ranking_count": 2,
                "selected_bundle_rank": 1,
            },
            payload=GateDecisionEmittedPayload(
                stage_name="bundle_compatibility",
                verdict=Verdict.PASS,
                unanimous_pass_required=False,
            ),
        ),
    )
    ig = client.get(f"/v1/runs/{run_id}/timeline").json()["integrator_gate"]
    assert ig["bundle_compatibility_ranking_count"] == 2
    assert ig["selected_bundle_rank"] == 1
    assert ig["selected_bundle_id"] == "auth-rbac-starter"
    assert len(ig["bundle_compatibility_ranking"]) == 2


def test_timeline_integrator_gate_excludes_optional_ranking_fields_without_ranking_metadata(
    client: TestClient,
) -> None:
    r = client.post("/v1/runs", json={"workflow_profile": "default"})
    run_id = UUID(r.json()["run_id"])
    eid = uuid4()
    store = client.app.state.store
    store.append(
        GateDecisionEmittedEvent(
            event_type=EventType.GATE_DECISION_EMITTED,
            event_id=eid,
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata={
                "integrator_gate": True,
                "bundle_id": "auth-rbac-starter",
                "integrator_score": 0.9,
            },
            payload=GateDecisionEmittedPayload(
                stage_name="bundle_compatibility",
                verdict=Verdict.PASS,
                unanimous_pass_required=False,
            ),
        ),
    )
    ig = client.get(f"/v1/runs/{run_id}/timeline").json()["integrator_gate"]
    assert ig["event_id"] == str(eid)
    assert "bundle_compatibility_ranking" not in ig
    assert "bundle_compatibility_ranking_count" not in ig
    assert "selected_bundle_rank" not in ig
    assert "selected_bundle_id" not in ig


def test_timeline_agent_evaluator_llm_policy_fields(client: TestClient) -> None:
    from agent_core.models import StageStartedEvent, StageStartedPayload

    r = client.post("/v1/runs", json={"workflow_profile": "default"})
    run_id = UUID(r.json()["run_id"])
    eid = uuid4()
    client.app.state.store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=eid,
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata={
                "agent_evaluator": {
                    "evaluation": {"status": "ok", "gaps": []},
                    "evaluation_branch": "rules_with_llm_policy",
                    "llm_evaluation": {
                        "status": "needs_work",
                        "summary": "policy suggests more coverage",
                        "policy_score": 0.875,
                        "policy_score_band": "meets_threshold",
                    },
                },
            },
            payload=StageStartedPayload(stage_name="agent_eval:commerce", attempt=1),
        ),
    )
    ae = client.get(f"/v1/runs/{run_id}/timeline").json()["agent_evaluator"]
    assert ae["evaluation_branch"] == "rules_with_llm_policy"
    assert ae["evaluation_status"] == "ok"
    assert ae["llm_evaluation_summary"] == "policy suggests more coverage"
    assert ae["llm_evaluation_status"] == "needs_work"
    assert ae["llm_evaluation_score"] == 0.875
    assert ae["llm_evaluation_score_band"] == "meets_threshold"


def test_timeline_integrator_gate_history_lists_chronological_gates(client: TestClient) -> None:
    r = client.post("/v1/runs", json={"workflow_profile": "default"})
    run_id = UUID(r.json()["run_id"])
    store = client.app.state.store
    eid1 = uuid4()
    store.append(
        GateDecisionEmittedEvent(
            event_type=EventType.GATE_DECISION_EMITTED,
            event_id=eid1,
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata={
                "integrator_gate": True,
                "bundle_id": "b-first",
                "bundle_title": "First",
                "integrator_score": 0.5,
                "min_score_to_pass": 0.3,
                "integrator_project_tags": [],
                "integrator_bundle_tags": [],
                "integrator_matched_tags": [],
            },
            payload=GateDecisionEmittedPayload(
                stage_name="bundle_compatibility",
                verdict=Verdict.PASS,
                unanimous_pass_required=False,
            ),
        ),
    )
    eid2 = uuid4()
    store.append(
        GateDecisionEmittedEvent(
            event_type=EventType.GATE_DECISION_EMITTED,
            event_id=eid2,
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata={
                "integrator_gate": True,
                "bundle_id": "b-second",
                "bundle_title": "Second",
                "integrator_score": 0.9,
                "min_score_to_pass": 0.3,
                "integrator_project_tags": [],
                "integrator_bundle_tags": [],
                "integrator_matched_tags": [],
            },
            payload=GateDecisionEmittedPayload(
                stage_name="bundle_compatibility",
                verdict=Verdict.FAIL,
                unanimous_pass_required=False,
                failure_reason_code="integrator_below_threshold",
            ),
        ),
    )
    tl = client.get(f"/v1/runs/{run_id}/timeline").json()
    hist = tl["integrator_gate_history"]
    assert isinstance(hist, list) and len(hist) == 2
    assert hist[0]["bundle_id"] == "b-first"
    assert hist[0]["verdict"] == "PASS"
    assert hist[1]["bundle_id"] == "b-second"
    assert hist[1]["verdict"] == "FAIL"
    assert tl["integrator_gate"]["event_id"] == str(eid2)
    assert tl["integrator_gate"]["verdict"] == "FAIL"
    d = tl.get("integrator_gate_delta")
    assert d is not None
    assert d["integrator_score_delta"] == pytest.approx(0.4)
    assert d["verdict_changed"] is True
    assert d["bundle_id_changed"] is True
    assert d["previous_event_id"] == str(eid1)
    assert d["current_event_id"] == str(eid2)


def test_timeline_agent_evaluator_summary_from_stage_started_events(client: TestClient) -> None:
    r = client.post("/v1/runs", json={"workflow_profile": "default"})
    run_id = UUID(r.json()["run_id"])
    store = client.app.state.store
    eid_first = uuid4()
    store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=eid_first,
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=StageStartedPayload(stage_name="agent_eval:default", attempt=1),
        ),
    )
    tl = client.get(f"/v1/runs/{run_id}/timeline").json()
    ae = tl["agent_evaluator"]
    assert ae is not None
    assert ae["event_id"] == str(eid_first)
    assert ae["stage_name"] == "agent_eval:default"
    assert ae["persona_id"] == "default"
    assert ae["attempt"] == 1

    eid_second = uuid4()
    store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=eid_second,
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=StageStartedPayload(stage_name="agent_eval:backend_engineer", attempt=1),
        ),
    )
    tl2 = client.get(f"/v1/runs/{run_id}/timeline").json()
    ae2 = tl2["agent_evaluator"]
    assert ae2 is not None
    assert ae2["event_id"] == str(eid_second)
    assert ae2["stage_name"] == "agent_eval:backend_engineer"
    assert ae2["persona_id"] == "backend_engineer"


def test_timeline_agent_evaluator_includes_auto_create_persona_metadata(client: TestClient) -> None:
    r = client.post("/v1/runs", json={"workflow_profile": "default"})
    run_id = UUID(r.json()["run_id"])
    store = client.app.state.store
    eid = uuid4()
    store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=eid,
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata={
                "agent_evaluator": {
                    "auto_create_persona": {
                        "auto_create_persona_applied": True,
                        "shelf": "business_area",
                        "persona_id": "timeline_ae",
                    },
                },
            },
            payload=StageStartedPayload(stage_name="agent_eval:timeline_ae", attempt=1),
        ),
    )
    tl = client.get(f"/v1/runs/{run_id}/timeline").json()
    ae = tl["agent_evaluator"]
    assert ae is not None
    ac = ae.get("auto_create_persona")
    assert isinstance(ac, dict)
    assert ac.get("auto_create_persona_applied") is True


def test_timeline_agent_evaluator_includes_auto_promote_metadata(client: TestClient) -> None:
    r = client.post("/v1/runs", json={"workflow_profile": "default"})
    run_id = UUID(r.json()["run_id"])
    store = client.app.state.store
    eid = uuid4()
    store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=eid,
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata={
                "agent_evaluator": {
                    "auto_promote_probation_requested": True,
                    "auto_promote_probation_applied": False,
                    "reason": "env_kill_switch",
                },
            },
            payload=StageStartedPayload(stage_name="agent_eval:commerce", attempt=1),
        ),
    )
    tl = client.get(f"/v1/runs/{run_id}/timeline").json()
    ae = tl["agent_evaluator"]
    assert ae is not None
    assert ae["event_id"] == str(eid)
    assert ae["persona_id"] == "commerce"
    ap = ae.get("auto_promote")
    assert isinstance(ap, dict)
    assert ap.get("reason") == "env_kill_switch"
    assert ap.get("auto_promote_probation_applied") is False
    assert ae.get("auto_promote_requested") is True
    assert ae.get("auto_promote_applied") is False
    assert ae.get("auto_promote_reason") == "env_kill_switch"


def test_timeline_self_refinement_summary_from_stage_started_events(client: TestClient) -> None:
    r = client.post("/v1/runs", json={"workflow_profile": "default"})
    run_id = UUID(r.json()["run_id"])
    store = client.app.state.store
    eid_first = uuid4()
    store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=eid_first,
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata={
                "self_refinement": {
                    "version": "v1",
                    "description": "first pass",
                    "llm_critique": {"summary": "llm says hold"},
                },
            },
            payload=StageStartedPayload(stage_name="self_refinement:policy", attempt=1),
        ),
    )
    tl = client.get(f"/v1/runs/{run_id}/timeline").json()
    sr = tl["self_refinement"]
    assert sr is not None
    assert sr["event_id"] == str(eid_first)
    assert sr["stage_name"] == "self_refinement:policy"
    assert sr["attempt"] == 1
    assert sr["version"] == "v1"
    assert sr["description"] == "first pass"
    assert sr["llm_critique_summary"] == "llm says hold"
    assert sr["marker_count"] == 1
    assert sr["first_marker_occurred_at"] == sr["occurred_at"]
    assert sr["last_marker_occurred_at"] == sr["occurred_at"]
    assert "max_iterations_exceeded" not in sr

    eid_second = uuid4()
    first_occ = sr["occurred_at"]
    store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=eid_second,
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata={
                "self_refinement": {
                    "version": "v2",
                    "description": "second wins",
                },
            },
            payload=StageStartedPayload(stage_name="self_refinement:policy", attempt=1),
        ),
    )
    tl2 = client.get(f"/v1/runs/{run_id}/timeline").json()
    sr2 = tl2["self_refinement"]
    assert sr2 is not None
    assert sr2["event_id"] == str(eid_second)
    assert sr2["version"] == "v2"
    assert sr2["description"] == "second wins"
    assert sr2["marker_count"] == 2
    assert sr2["first_marker_occurred_at"] == first_occ
    assert sr2["last_marker_occurred_at"] == sr2["occurred_at"]


def test_timeline_self_refinement_phase_d_signal_from_event(client: TestClient) -> None:
    r = client.post("/v1/runs", json={"workflow_profile": "default"})
    run_id = UUID(r.json()["run_id"])
    store = client.app.state.store
    store.append(
        SelfRefinementLoopSignalledEvent(
            event_type=EventType.SELF_REFINEMENT_LOOP_SIGNALLED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=SelfRefinementLoopSignalledPayload(
                attempt=1,
                max_iterations=3,
            ),
        ),
    )
    store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata={"self_refinement": {"version": "v1", "description": "first pass"}},
            payload=StageStartedPayload(stage_name="self_refinement:policy", attempt=1),
        ),
    )
    tl = client.get(f"/v1/runs/{run_id}/timeline").json()
    sr = tl["self_refinement"]
    assert isinstance(sr, dict)
    phase_d = sr.get("phase_d_signal")
    assert isinstance(phase_d, dict)
    assert phase_d.get("signal") == "phase_d_kickoff"
    assert phase_d.get("gate_decision") == "hold"
    assert phase_d.get("loops_remaining") == 0
    assert phase_d.get("orchestration_branch") == "rules"


def test_timeline_self_refinement_llm_critique_stage_from_gate(client: TestClient) -> None:
    r = client.post("/v1/runs", json={"workflow_profile": "default"})
    run_id = UUID(r.json()["run_id"])
    store = client.app.state.store
    store.append(
        GateDecisionEmittedEvent(
            event_type=EventType.GATE_DECISION_EMITTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=GateDecisionEmittedPayload(
                stage_name="self_refinement.critique",
                verdict=Verdict.PASS,
                unanimous_pass_required=True,
            ),
        ),
    )
    store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata={"self_refinement": {"version": "v1"}},
            payload=StageStartedPayload(stage_name="self_refinement:policy", attempt=1),
        ),
    )
    sr = client.get(f"/v1/runs/{run_id}/timeline").json()["self_refinement"]
    assert isinstance(sr, dict)
    panel = sr.get("llm_critique_stage")
    assert isinstance(panel, dict)
    assert panel.get("stage_name") == "self_refinement.critique"
    assert panel.get("verdict") == "PASS"


def test_timeline_self_refinement_marker_history(client: TestClient) -> None:
    r = client.post("/v1/runs", json={"workflow_profile": "default"})
    run_id = UUID(r.json()["run_id"])
    store = client.app.state.store
    for i, ver in enumerate(("v1", "v2", "v3"), start=1):
        store.append(
            StageStartedEvent(
                event_type=EventType.STAGE_STARTED,
                event_id=uuid4(),
                run_id=run_id,
                occurred_at=datetime.now(timezone.utc),
                metadata={"self_refinement": {"version": ver}},
                payload=StageStartedPayload(
                    stage_name="self_refinement:policy",
                    attempt=i,
                ),
            ),
        )
    tl = client.get(f"/v1/runs/{run_id}/timeline").json()
    hist = tl["self_refinement_marker_history"]
    assert hist is not None
    assert len(hist) == 3
    assert [h["version"] for h in hist] == ["v1", "v2", "v3"]
    assert tl["self_refinement"]["marker_count"] == 3


def test_timeline_scraper_fetch_summary_from_stage_events(client: TestClient) -> None:
    r = client.post("/v1/runs", json={"workflow_profile": "default"})
    run_id = UUID(r.json()["run_id"])
    store = client.app.state.store
    tl0 = client.get(f"/v1/runs/{run_id}/timeline").json()
    assert tl0["scraper_fetch"] is None

    eid_pass = uuid4()
    store.append(
        StagePassedEvent(
            event_type=EventType.STAGE_PASSED,
            event_id=eid_pass,
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata={
                "scraper_fetch": {
                    "fetches": [
                        {"url_host": "example.com", "bytes": 100, "http_status": 200},
                        {"url_host": "other.com", "bytes": 50, "http_status": 200},
                    ],
                },
            },
            payload=StagePassedPayload(stage_name="scraper:fetch", duration_ms=12),
        ),
    )
    tl = client.get(f"/v1/runs/{run_id}/timeline").json()
    sf = tl["scraper_fetch"]
    assert sf is not None
    assert sf["event_id"] == str(eid_pass)
    assert sf["outcome"] == "passed"
    assert sf["fetch_count"] == 2
    assert sf["total_bytes"] == 150
    assert sf.get("reason_code") is None
    fetches = sf.get("fetches")
    assert isinstance(fetches, list)
    assert len(fetches) == 2
    assert fetches[0]["url_host"] == "example.com"
    assert fetches[0]["bytes"] == 100

    eid_fail = uuid4()
    store.append(
        StageFailedEvent(
            event_type=EventType.STAGE_FAILED,
            event_id=eid_fail,
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata={
                "scraper_fetch": {
                    "fetches": [{"url_host": "a.com", "bytes": 10}],
                    "failed_url_host": "b.com",
                },
            },
            payload=StageFailedPayload(
                stage_name="scraper:fetch",
                reason_code="scraper_budget_exceeded",
                message="no bytes remaining",
            ),
        ),
    )
    tl2 = client.get(f"/v1/runs/{run_id}/timeline").json()
    sf2 = tl2["scraper_fetch"]
    assert sf2 is not None
    assert sf2["event_id"] == str(eid_fail)
    assert sf2["outcome"] == "failed"
    assert sf2["reason_code"] == "scraper_budget_exceeded"
    assert sf2["fetch_count"] == 1
    assert sf2["total_bytes"] == 10
    assert sf2["failed_url_host"] == "b.com"


def test_timeline_universal_critique_summary_from_gate_events(client: TestClient) -> None:
    r = client.post("/v1/runs", json={"workflow_profile": "default"})
    run_id = UUID(r.json()["run_id"])
    store = client.app.state.store
    tl0 = client.get(f"/v1/runs/{run_id}/timeline").json()
    assert tl0["universal_critique"] is None

    store.append(
        GateDecisionEmittedEvent(
            event_type=EventType.GATE_DECISION_EMITTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata={},
            payload=GateDecisionEmittedPayload(
                stage_name="planner.critique",
                verdict=Verdict.PASS,
            ),
        ),
    )
    store.append(
        GateDecisionEmittedEvent(
            event_type=EventType.GATE_DECISION_EMITTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata={},
            payload=GateDecisionEmittedPayload(
                stage_name="implementation.critique",
                verdict=Verdict.FAIL,
                failure_reason_code="critique_fail",
            ),
        ),
    )
    tl = client.get(f"/v1/runs/{run_id}/timeline").json()
    uc = tl["universal_critique"]
    assert uc is not None
    assert uc["stage_count"] == 2
    assert uc["fail_count"] == 1
    assert uc["pass_count"] == 1
    assert uc["fail_rate"] == 0.5
    assert uc["distinct_fail_stages"] == ["implementation.critique"]
    stages = uc["stages"]
    assert len(stages) == 2
    assert stages[0]["stage_name"] == "planner.critique"
    assert stages[1]["stage_name"] == "implementation.critique"
    assert stages[1]["verdict"] == "FAIL"

    eid_tw = uuid4()
    store.append(
        GateDecisionEmittedEvent(
            event_type=EventType.GATE_DECISION_EMITTED,
            event_id=eid_tw,
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata={},
            payload=GateDecisionEmittedPayload(
                stage_name="test_writer.critique",
                verdict=Verdict.PASS,
            ),
        ),
    )
    tl2 = client.get(f"/v1/runs/{run_id}/timeline").json()
    uc2 = tl2["universal_critique"]
    assert uc2["stage_count"] == 3
    assert uc2["pass_count"] == 2
    by_name = {s["stage_name"]: s for s in uc2["stages"]}
    assert by_name["test_writer.critique"]["event_id"] == str(eid_tw)
    store.append(
        GateDecisionEmittedEvent(
            event_type=EventType.GATE_DECISION_EMITTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata={},
            payload=GateDecisionEmittedPayload(
                stage_name="frontend_writer.critique",
                verdict=Verdict.PASS,
            ),
        ),
    )
    store.append(
        GateDecisionEmittedEvent(
            event_type=EventType.GATE_DECISION_EMITTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata={},
            payload=GateDecisionEmittedPayload(
                stage_name="module_integrator.critique",
                verdict=Verdict.PASS,
            ),
        ),
    )
    tl3 = client.get(f"/v1/runs/{run_id}/timeline").json()
    uc3 = tl3["universal_critique"]
    assert uc3["stage_count"] == 5
    assert uc3["pass_count"] == 4
    assert uc3["distinct_fail_stages"] == ["implementation.critique"]
    assert [s["stage_name"] for s in uc3["stages"]] == [
        "planner.critique",
        "implementation.critique",
        "test_writer.critique",
        "frontend_writer.critique",
        "module_integrator.critique",
    ]


def test_timeline_universal_critique_ignores_integrator_gate(client: TestClient) -> None:
    r = client.post("/v1/runs", json={"workflow_profile": "default"})
    run_id = UUID(r.json()["run_id"])
    store = client.app.state.store
    store.append(
        GateDecisionEmittedEvent(
            event_type=EventType.GATE_DECISION_EMITTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata={"integrator_gate": True, "bundle_id": "b1"},
            payload=GateDecisionEmittedPayload(
                stage_name="integrator",
                verdict=Verdict.PASS,
            ),
        ),
    )
    tl = client.get(f"/v1/runs/{run_id}/timeline").json()
    assert tl["universal_critique"] is None
    assert tl["integrator_gate"] is not None


def test_timeline_scraper_fetch_ignores_non_scraper_stages(client: TestClient) -> None:
    r = client.post("/v1/runs", json={"workflow_profile": "default"})
    run_id = UUID(r.json()["run_id"])
    store = client.app.state.store
    store.append(
        StagePassedEvent(
            event_type=EventType.STAGE_PASSED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata={},
            payload=StagePassedPayload(stage_name="plan", duration_ms=1),
        ),
    )
    tl = client.get(f"/v1/runs/{run_id}/timeline").json()
    assert tl["scraper_fetch"] is None


def test_timeline_run_escalated_summary_from_events(client: TestClient) -> None:
    r = client.post("/v1/runs", json={"workflow_profile": "default"})
    run_id = UUID(r.json()["run_id"])
    store = client.app.state.store
    eid_first = uuid4()
    store.append(
        RunEscalatedEvent(
            event_type=EventType.RUN_ESCALATED,
            event_id=eid_first,
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=RunEscalatedPayload(
                actor_id="human",
                reason_code="THRESHOLD",
                policy_snapshot_id="snap-1",
                notes="first escalation",
            ),
        ),
    )
    tl = client.get(f"/v1/runs/{run_id}/timeline").json()
    esc = tl["run_escalated"]
    assert esc is not None
    assert esc["event_id"] == str(eid_first)
    assert esc["actor_id"] == "human"
    assert esc["reason_code"] == "THRESHOLD"
    assert esc["policy_snapshot_id"] == "snap-1"
    assert esc["notes"] == "first escalation"

    eid_second = uuid4()
    store.append(
        RunEscalatedEvent(
            event_type=EventType.RUN_ESCALATED,
            event_id=eid_second,
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=RunEscalatedPayload(
                actor_id="system",
                reason_code="ANTI_DEADLOCK",
                policy_snapshot_id=None,
                notes="second wins",
            ),
        ),
    )
    tl2 = client.get(f"/v1/runs/{run_id}/timeline").json()
    esc2 = tl2["run_escalated"]
    assert esc2 is not None
    assert esc2["event_id"] == str(eid_second)
    assert esc2["reason_code"] == "ANTI_DEADLOCK"
    assert esc2["notes"] == "second wins"
    assert esc2["actor_id"] == "system"


def test_timeline_run_escalated_history_and_delta(client: TestClient) -> None:
    r = client.post("/v1/runs", json={"workflow_profile": "default"})
    run_id = UUID(r.json()["run_id"])
    store = client.app.state.store
    eid_first = uuid4()
    store.append(
        RunEscalatedEvent(
            event_type=EventType.RUN_ESCALATED,
            event_id=eid_first,
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=RunEscalatedPayload(
                actor_id="human",
                reason_code="THRESHOLD",
                policy_snapshot_id="snap-1",
                notes="first",
            ),
        ),
    )
    tl_one = client.get(f"/v1/runs/{run_id}/timeline").json()
    assert tl_one["run_escalated_history"] is not None
    assert len(tl_one["run_escalated_history"]) == 1
    assert tl_one["run_escalated_delta"] is None

    eid_second = uuid4()
    store.append(
        RunEscalatedEvent(
            event_type=EventType.RUN_ESCALATED,
            event_id=eid_second,
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=RunEscalatedPayload(
                actor_id="system",
                reason_code="ANTI_DEADLOCK",
                policy_snapshot_id=None,
                notes="second",
            ),
        ),
    )
    tl2 = client.get(f"/v1/runs/{run_id}/timeline").json()
    hist = tl2["run_escalated_history"]
    assert hist is not None
    assert len(hist) == 2
    assert hist[0]["reason_code"] == "THRESHOLD"
    assert hist[1]["reason_code"] == "ANTI_DEADLOCK"
    assert tl2["run_escalated"]["event_id"] == str(eid_second)
    delta = tl2["run_escalated_delta"]
    assert delta is not None
    assert delta["reason_code_changed"] is True
    assert delta["previous_reason_code"] == "THRESHOLD"
    assert delta["current_reason_code"] == "ANTI_DEADLOCK"
    assert delta["actor_id_changed"] is True


_BACKEND_WRITER = UUID("44444444-4444-4444-8444-444444444404")


def test_timeline_security_scan_on_verify_summary_from_finding_events(client: TestClient) -> None:
    r = client.post("/v1/runs", json={"workflow_profile": "default"})
    run_id = UUID(r.json()["run_id"])
    store = client.app.state.store
    fid_plain = uuid4()
    eid_plain = uuid4()
    store.append(
        FindingCreatedEvent(
            event_type=EventType.FINDING_CREATED,
            event_id=eid_plain,
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata={},
            payload=FindingCreatedPayload(
                finding_id=fid_plain,
                category="verify",
                owner_role=_BACKEND_WRITER,
                severity=Severity.LOW,
                source_artifact="writer_verifier_bundle",
                repro_steps=["no scan"],
                required_fixes=[],
            ),
        ),
    )
    tl0 = client.get(f"/v1/runs/{run_id}/timeline").json()
    assert tl0["security_scan_on_verify"] is None

    fid_first = uuid4()
    eid_first = uuid4()
    store.append(
        FindingCreatedEvent(
            event_type=EventType.FINDING_CREATED,
            event_id=eid_first,
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata={
                "security_scan_exit": 0,
                "security_scan_ruff_exit": 0,
                "security_scan_bandit_exit": 0,
                "security_scan_snippet": "bandit ok\n",
            },
            payload=FindingCreatedPayload(
                finding_id=fid_first,
                category="verify",
                owner_role=_BACKEND_WRITER,
                severity=Severity.LOW,
                source_artifact="writer_verifier_bundle",
                repro_steps=["fail"],
                required_fixes=[],
            ),
        ),
    )
    tl = client.get(f"/v1/runs/{run_id}/timeline").json()
    ss = tl["security_scan_on_verify"]
    assert ss is not None
    assert ss["event_id"] == str(eid_first)
    assert ss["finding_id"] == str(fid_first)
    assert ss["category"] == "verify"
    assert ss["security_scan_exit"] == 0
    assert ss["security_scan_ruff_exit"] == 0
    assert ss["security_scan_bandit_exit"] == 0
    assert ss["security_scan_snippet"] == "bandit ok\n"

    fid_second = uuid4()
    eid_second = uuid4()
    store.append(
        FindingCreatedEvent(
            event_type=EventType.FINDING_CREATED,
            event_id=eid_second,
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata={
                "security_scan_exit": 1,
                "security_scan_ruff_exit": 2,
                "security_scan_bandit_exit": 0,
                "security_scan_snippet": "second wins",
            },
            payload=FindingCreatedPayload(
                finding_id=fid_second,
                category="verify",
                owner_role=_BACKEND_WRITER,
                severity=Severity.LOW,
                source_artifact="writer_verifier_bundle",
                repro_steps=["fail2"],
                required_fixes=[],
            ),
        ),
    )
    tl2 = client.get(f"/v1/runs/{run_id}/timeline").json()
    ss2 = tl2["security_scan_on_verify"]
    assert ss2 is not None
    assert ss2["event_id"] == str(eid_second)
    assert ss2["finding_id"] == str(fid_second)
    assert ss2["security_scan_exit"] == 1
    assert ss2["security_scan_ruff_exit"] == 2
    assert ss2["security_scan_bandit_exit"] == 0
    assert ss2["security_scan_snippet"] == "second wins"
    hist = tl2["security_scan_on_verify_history"]
    assert hist is not None
    assert len(hist) == 2
    assert hist[0]["event_id"] == str(eid_first)
    assert hist[1]["event_id"] == str(eid_second)
    assert hist[1]["security_scan_exit"] == 1


def test_timeline_preflight_summary_from_passed_event(client: TestClient) -> None:
    """fo124: ``GET /v1/runs/{id}/timeline`` exposes a top-level ``preflight`` summary.

    Three assertions:

    * Run without ``model.preflight.passed`` ⇒ ``preflight is None``.
    * After appending a multisample passed event, the projection includes the
      new ``health_latency_samples_ms`` list intact.
    * A second passed event wins (matches the ``latest wins`` convention used
      by the sibling timeline-summary helpers).
    """
    r = client.post("/v1/runs", json={"workflow_profile": "default"})
    run_id = UUID(r.json()["run_id"])
    store = client.app.state.store

    tl0 = client.get(f"/v1/runs/{run_id}/timeline").json()
    assert tl0["preflight"] is None

    eid_first = uuid4()
    store.append(
        ModelPreflightPassedEvent(
            event_type=EventType.MODEL_PREFLIGHT_PASSED,
            event_id=eid_first,
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=ModelPreflightPassedPayload(
                provider="ollama",
                validated_model_id="llama3.1:8b",
                context_tokens=8192,
                p95_latency_ms=135,
                checks_passed=[
                    "runtime_reachable",
                    "model_available",
                    "health_latency_measured",
                    "health_latency_multisample",
                    "context_budget_ok",
                ],
                preflight_latency_sample_count=3,
                p95_latency_source="max(health_p95_ms,show_latency_ms,optional_json_probe)",
                health_latency_samples_ms=[120, 130, 135],
            ),
        ),
    )
    tl = client.get(f"/v1/runs/{run_id}/timeline").json()
    pf = tl["preflight"]
    assert pf is not None
    assert pf["event_id"] == str(eid_first)
    assert pf["provider"] == "ollama"
    assert pf["validated_model_id"] == "llama3.1:8b"
    assert pf["context_tokens"] == 8192
    assert pf["p95_latency_ms"] == 135
    assert pf["preflight_latency_sample_count"] == 3
    assert pf["health_latency_samples_ms"] == [120, 130, 135]
    assert "health_latency_multisample" in pf["checks_passed"]

    eid_second = uuid4()
    store.append(
        ModelPreflightPassedEvent(
            event_type=EventType.MODEL_PREFLIGHT_PASSED,
            event_id=eid_second,
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=ModelPreflightPassedPayload(
                provider="ollama",
                validated_model_id="qwen2.5-coder:14b",
                context_tokens=16384,
                p95_latency_ms=200,
                preflight_latency_sample_count=5,
                health_latency_samples_ms=[180, 190, 200, 210, 220],
            ),
        ),
    )
    tl2 = client.get(f"/v1/runs/{run_id}/timeline").json()
    pf2 = tl2["preflight"]
    assert pf2 is not None
    assert pf2["event_id"] == str(eid_second)
    assert pf2["validated_model_id"] == "qwen2.5-coder:14b"
    assert pf2["health_latency_samples_ms"] == [180, 190, 200, 210, 220]


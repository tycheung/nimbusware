"""Self-refinement rules loop v1 (P2-a / §14 #17)."""

from __future__ import annotations

from pathlib import Path
import os
from unittest.mock import patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from nimbusware_api.app import app
from nimbusware_api.deps import get_orchestrator, get_store
from nimbusware_config.materializer import ConfigMaterializer
from nimbusware_config.seed import seed_config_from_repo
from nimbusware_config.store import InMemoryConfigStore
from hermes_extensions.personas import PersonaShelf
from hermes_extensions.self_refinement import SelfRefinementEvaluator
from hermes_orchestrator.pipeline import RunOrchestrator, default_paths, make_dev_orchestrator
from hermes_orchestrator.workflow_self_refinement import SelfRefinementWorkflowBlock
from hermes_store.memory import InMemoryEventStore


def _minimal_shelf(*, probation_status: str | None = None, with_profile: bool = True) -> PersonaShelf:
    ba: dict[str, object] = {"id": "commerce", "display_name": "Commerce", "version": 1}
    dr: dict[str, object] = {
        "id": "backend_engineer",
        "display_name": "Backend",
        "version": 1,
    }
    if with_profile:
        ba["capability_profile"] = "Commerce domain expertise"
        ba["boundary_statement"] = "No payment processing"
        dr["capability_profile"] = "Backend API design"
        dr["boundary_statement"] = "No infra provisioning"
    if probation_status is not None:
        ba["probation_status"] = probation_status
        dr["probation_status"] = probation_status
    return PersonaShelf.from_content(
        {
            "version": 1,
            "business_area": [ba],
            "development_role": [dr],
        },
    )


def test_self_refinement_evaluator_ok_with_promoted_personas() -> None:
    shelf = _minimal_shelf(probation_status="promoted")
    out = SelfRefinementEvaluator().evaluate(
        persona_assignment={
            "business_area": {"id": "commerce"},
            "development_role": {"id": "backend_engineer"},
        },
        shelf=shelf,
    )
    assert out["status"] == "ok"
    assert out["promotion_ready"] is True
    assert out["gaps"] == []


def test_self_refinement_evaluator_gap_without_assignment() -> None:
    out = SelfRefinementEvaluator().evaluate(
        persona_assignment=None,
        shelf=_minimal_shelf(probation_status="promoted"),
    )
    assert out["status"] == "gap"
    assert out["promotion_ready"] is False
    assert "no_persona_assignment_on_run" in out["gaps"]


def test_self_refinement_evaluator_invalid_missing_or_probation() -> None:
    out_missing = SelfRefinementEvaluator().evaluate(
        persona_assignment={"business_area": {"id": "missing"}},
        shelf=_minimal_shelf(probation_status="promoted"),
    )
    assert out_missing["status"] == "invalid"
    assert any("business_area_not_on_shelf" in g for g in out_missing["gaps"])

    out_probation = SelfRefinementEvaluator().evaluate(
        persona_assignment={
            "business_area": {"id": "commerce"},
            "development_role": {"id": "backend_engineer"},
        },
        shelf=_minimal_shelf(probation_status="probation"),
    )
    assert out_probation["status"] == "invalid"
    assert any("probation_not_cleared" in g for g in out_probation["gaps"])


def test_self_refinement_evaluator_v2_gap_missing_profile_and_boundary() -> None:
    out = SelfRefinementEvaluator().evaluate(
        persona_assignment={
            "business_area": {"id": "commerce"},
            "development_role": {"id": "backend_engineer"},
        },
        shelf=_minimal_shelf(probation_status="promoted", with_profile=False),
    )
    assert out["status"] == "invalid"
    assert out["promotion_ready"] is False
    assert any("capability_profile_missing" in g for g in out["gaps"])
    assert any("boundary_statement_missing" in g for g in out["gaps"])


def test_self_refinement_marker_increments_attempt() -> None:
    orch, mem = make_dev_orchestrator()
    rid = orch.create_run(
        "self_refinement_on",
        business_area_persona_id="commerce",
        development_role_persona_id="backend_engineer",
    )
    orch._maybe_emit_self_refinement_stage_marker(rid)  # noqa: SLF001
    orch._maybe_emit_self_refinement_stage_marker(rid)  # noqa: SLF001
    markers = [
        r
        for r in mem.list_run_events(str(rid))
        if r.get("event_type") == "stage.started"
        and (r.get("payload") or {}).get("stage_name") == "self_refinement:policy"
    ]
    assert [m.get("payload", {}).get("attempt") for m in markers] == [1, 2]


def test_self_refinement_max_iterations_emits_stage_failed() -> None:
    orch, mem = make_dev_orchestrator()
    rid = orch.create_run("self_refinement_on")
    block = SelfRefinementWorkflowBlock(enabled=True, max_iterations=2)
    with patch(
        "hermes_orchestrator.pipeline.parse_self_refinement_workflow_block",
        return_value=block,
    ):
        for _ in range(3):
            orch._maybe_emit_self_refinement_stage_marker(rid)  # noqa: SLF001
    markers = [
        r
        for r in mem.list_run_events(str(rid))
        if r.get("event_type") == "stage.started"
        and (r.get("payload") or {}).get("stage_name") == "self_refinement:policy"
    ]
    assert len(markers) == 2
    failed = [
        r
        for r in mem.list_run_events(str(rid))
        if r.get("event_type") == "stage.failed"
        and (r.get("payload") or {}).get("reason_code") == "self_refinement_max_iterations"
    ]
    assert len(failed) == 1


def test_self_refinement_marker_attaches_evaluation_metadata() -> None:
    orch, mem = make_dev_orchestrator()
    rid = orch.create_run(
        "self_refinement_on",
        business_area_persona_id="commerce",
        development_role_persona_id="backend_engineer",
    )
    orch._maybe_emit_self_refinement_stage_marker(rid)  # noqa: SLF001
    evs = mem.list_run_events(str(rid))
    stage = next(
        r
        for r in evs
        if r.get("event_type") == "stage.started"
        and (r.get("payload") or {}).get("stage_name") == "self_refinement:policy"
    )
    eval_meta = ((stage.get("metadata") or {}).get("self_refinement") or {}).get("evaluation")
    assert isinstance(eval_meta, dict)
    assert eval_meta.get("status") in {"ok", "invalid"}
    assert "promotion_ready" in eval_meta
    sr_meta = (stage.get("metadata") or {}).get("self_refinement") or {}
    assert sr_meta.get("signal") == "phase_d_kickoff"
    assert sr_meta.get("gate_decision") in {"hold", "proceed"}
    assert isinstance(sr_meta.get("loops_remaining"), int)
    assert isinstance(sr_meta.get("iteration_progress_ratio"), float)
    assert isinstance(sr_meta.get("should_continue"), bool)


def test_timeline_self_refinement_includes_evaluation_fields() -> None:
    root = Path(__file__).resolve().parents[1]
    base, _ = default_paths(root)
    cfg_store = InMemoryConfigStore()
    seed_config_from_repo(root, cfg_store)
    mat = ConfigMaterializer(root, store=cfg_store, use_db=True)
    ev_store = InMemoryEventStore()
    orch = RunOrchestrator(
        ev_store,
        mat.get_role_registry(),
        repo_root=root,
        base_config_path=base,
        config_materializer=mat,
    )
    app.dependency_overrides[get_orchestrator] = lambda: orch
    app.dependency_overrides[get_store] = lambda: ev_store
    try:
        with TestClient(app) as c:
            r = c.post(
                "/v1/runs",
                json={
                    "workflow_profile": "self_refinement_on",
                    "business_area_persona_id": "commerce",
                    "development_role_persona_id": "backend_engineer",
                },
            )
            assert r.status_code == 200, r.text
            run_id = r.json()["run_id"]
            with patch.dict(
                os.environ,
                {"HERMES_SELF_REFINEMENT_STAGE_MARKER": "1"},
                clear=False,
            ):
                orch._maybe_emit_self_refinement_stage_marker(UUID(run_id))  # noqa: SLF001
            tl = c.get(f"/v1/runs/{run_id}/timeline").json()
            sr = tl.get("self_refinement")
            assert isinstance(sr, dict)
            assert sr.get("evaluation_status") in {"ok", "invalid", "gap"}
            assert "promotion_ready" in sr
            phase_d = sr.get("phase_d_signal")
            assert isinstance(phase_d, dict)
            assert phase_d.get("signal") == "phase_d_kickoff"
            assert phase_d.get("gate_decision") in {"proceed", "hold"}
            assert phase_d.get("evaluation_status") in {"ok", "invalid", "gap"}
            assert phase_d.get("loops_remaining") == 2
            assert isinstance(phase_d.get("iteration_progress_ratio"), float)
            assert isinstance(phase_d.get("should_continue"), bool)
            assert sr.get("gate_decision") in {"proceed", "hold"}
            assert sr.get("loops_remaining") == 2
            assert isinstance(sr.get("iteration_progress_ratio"), float)
            assert isinstance(sr.get("should_continue"), bool)
            assert sr.get("orchestration_branch") in {"rules", "rules_with_llm_critique"}
    finally:
        app.dependency_overrides.pop(get_orchestrator, None)
        app.dependency_overrides.pop(get_store, None)

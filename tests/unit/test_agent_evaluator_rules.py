"""Agent evaluator rules loop v1 (P1-c / §14 #15)."""

from __future__ import annotations
from nimbusware_env import find_repo_root

from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from nimbusware_api.app import app
from nimbusware_api.deps import get_orchestrator, get_store
from nimbusware_config.materializer import ConfigMaterializer
from nimbusware_config.seed import seed_config_from_repo
from nimbusware_config.store import InMemoryConfigStore
from hermes_extensions.personas import PersonaShelf
from hermes_extensions.phase2 import (
    AGENT_EVALUATOR_PROMOTION_SCORE_THRESHOLD,
    AGENT_EVALUATOR_STRONG_SCORE_THRESHOLD,
    AgentEvaluator,
    agent_evaluator_score_band,
)
from hermes_orchestrator.pipeline import RunOrchestrator, default_paths, make_dev_orchestrator
from hermes_store.memory import InMemoryEventStore


def _minimal_shelf() -> PersonaShelf:
    raw = {
        "version": 1,
        "business_area": [{"id": "commerce", "display_name": "Commerce", "version": 1}],
        "development_role": [
            {"id": "backend_engineer", "display_name": "Backend", "version": 1},
        ],
    }
    return PersonaShelf.from_content(raw)


def test_agent_evaluator_evaluate_ok_with_assignment() -> None:
    shelf = _minimal_shelf()
    result = AgentEvaluator().evaluate(
        "commerce",
        persona_assignment={
            "business_area": {"id": "commerce"},
            "development_role": {"id": "backend_engineer"},
        },
        shelf=shelf,
    )
    assert result["status"] == "ok"
    assert result["gaps"] == []
    assert result["coverage"]["business_area"]["id"] == "commerce"
    assert float(result["score"]) >= 0.75
    assert result["promotion_ready"] is True
    assert result["score_band"] == "strong"


def test_agent_evaluator_score_band_thresholds() -> None:
    assert agent_evaluator_score_band(0.5) == "below_threshold"
    assert agent_evaluator_score_band(
        AGENT_EVALUATOR_PROMOTION_SCORE_THRESHOLD,
    ) == "meets_threshold"
    assert agent_evaluator_score_band(
        AGENT_EVALUATOR_STRONG_SCORE_THRESHOLD,
    ) == "strong"


def test_agent_evaluator_evaluate_invalid_missing_shelf_id() -> None:
    shelf = _minimal_shelf()
    result = AgentEvaluator().evaluate(
        "commerce",
        persona_assignment={"business_area": {"id": "missing-persona"}},
        shelf=shelf,
    )
    assert result["status"] == "invalid"
    assert any("business_area_not_on_shelf" in g for g in result["gaps"])
    assert float(result["score"]) < 0.75
    assert result["promotion_ready"] is False


def test_agent_evaluator_evaluate_gap_default_without_assignment() -> None:
    shelf = _minimal_shelf()
    result = AgentEvaluator().evaluate("default", persona_assignment=None, shelf=shelf)
    assert result["status"] == "gap"
    assert "no_persona_assignment_on_run" in result["gaps"]
    assert result["promotion_ready"] is False


def test_agent_evaluator_hook_attaches_evaluation_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HERMES_AGENT_EVALUATOR", "1")
    orch, mem = make_dev_orchestrator()
    rid = orch.create_run(
        "default",
        business_area_persona_id="commerce",
        development_role_persona_id="backend_engineer",
    )
    orch._maybe_emit_agent_evaluator_stage(rid)  # noqa: SLF001
    evs = mem.list_run_events(str(rid))
    stage = next(
        r
        for r in evs
        if r.get("event_type") == "stage.started"
        and str((r.get("payload") or {}).get("stage_name", "")).startswith("agent_eval:")
    )
    evaluation = stage["metadata"]["agent_evaluator"]["evaluation"]
    assert evaluation["status"] == "ok"
    assert evaluation["coverage"]["business_area"]["id"] == "commerce"
    assert float(evaluation["score"]) >= 0.75
    assert evaluation["promotion_ready"] is True


def test_timeline_agent_evaluator_includes_evaluation_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HERMES_AGENT_EVALUATOR", "1")
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    base, _ = default_paths(root)
    store_cfg = InMemoryConfigStore()
    seed_config_from_repo(root, store_cfg)
    mat = ConfigMaterializer(root, store=store_cfg, use_db=True)
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
                    "workflow_profile": "default",
                    "business_area_persona_id": "commerce",
                    "development_role_persona_id": "backend_engineer",
                },
            )
            run_id = r.json()["run_id"]
            orch._maybe_emit_agent_evaluator_stage(UUID(run_id))  # noqa: SLF001
            tl = c.get(f"/v1/runs/{run_id}/timeline").json()
            ae = tl.get("agent_evaluator")
            assert ae is not None
            assert ae.get("evaluation_status") == "ok"
            assert ae.get("coverage_business_area_id") == "commerce"
            assert ae.get("coverage_development_role_id") == "backend_engineer"
            assert float(ae.get("evaluation_score", 0.0)) >= 0.75
            assert ae.get("evaluation_score_band") in (
                "meets_threshold",
                "strong",
            )
            assert float(ae.get("coverage_ratio", 0.0)) > 0.0
            assert ae.get("promotion_ready") is True
    finally:
        app.dependency_overrides.pop(get_orchestrator, None)
        app.dependency_overrides.pop(get_store, None)

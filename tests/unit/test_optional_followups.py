from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from env import find_repo_root

ROOT = find_repo_root(start=Path(__file__).resolve().parents[1])


def test_default_workflow_profile_is_micro_slice() -> None:
    from orchestrator.default_workflow_profile import default_workflow_profile

    os.environ.pop("NIMBUSWARE_DEFAULT_WORKFLOW_PROFILE", None)
    assert default_workflow_profile() == "micro_slice"


def test_default_workflow_profile_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    from orchestrator.default_workflow_profile import default_workflow_profile

    monkeypatch.setenv("NIMBUSWARE_DEFAULT_WORKFLOW_PROFILE", "default")
    assert default_workflow_profile() == "default"


def test_self_refinement_production_llm_without_global_use_llm() -> None:
    from orchestrator.workflow_self_refinement import (
        self_refinement_production_llm_critique_effective,
    )

    os.environ.pop("NIMBUSWARE_USE_LLM", None)
    assert (
        self_refinement_production_llm_critique_effective(
            ROOT,
            "nimbusware_production",
        )
        is True
    )


def test_scan_n_plus_one_heuristic_clean_repo() -> None:
    from orchestrator.performance_scan import scan_n_plus_one_heuristic

    code, out = scan_n_plus_one_heuristic(ROOT)
    assert code in (0, 1)
    assert isinstance(out, str)


@patch.dict(os.environ, {"NIMBUSWARE_SELF_REFINEMENT_STAGE_MARKER": "1"}, clear=False)
@patch(
    "orchestrator._pipeline.self_refinement_critique_emit.execute_self_refinement_critique_llm",
    return_value={
        "verdict": "PASS",
        "gate_decision": "proceed",
        "summary": "mock",
    },
)
@patch(
    "orchestrator.pipeline.RunOrchestrator._selected_model_for_run",
    return_value="test-model",
)
@patch(
    "extensions.self_refinement.SelfRefinementEvaluator.evaluate",
    return_value={"status": "gap", "gaps": ["missing persona depth"]},
)
def test_production_sr_llm_path_without_nimbusware_use_llm(
    _mock_eval: object,
    _mock_llm: object,
    _mock_model: object,
) -> None:
    from orchestrator.pipeline import make_dev_orchestrator

    os.environ.pop("NIMBUSWARE_USE_LLM", None)
    orch, mem = make_dev_orchestrator(repo_root=ROOT)
    rid = orch.create_run("nimbusware_production")
    orch._maybe_emit_self_refinement_stage_marker(rid)  # noqa: SLF001
    signals = [
        r
        for r in mem.list_run_events(str(rid))
        if r.get("event_type") == "self_refinement.loop.signalled"
    ]
    assert signals
    assert (signals[0].get("payload") or {}).get("llm_critique_attempted") is True


def test_bundle_editor_tags_from_text() -> None:
    from console.bundle_catalog_editor import bundle_editor_tags_from_text

    assert bundle_editor_tags_from_text("auth, rbac\nstripe") == [
        "auth",
        "rbac",
        "stripe",
    ]

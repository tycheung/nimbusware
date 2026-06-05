"""B1 promotion: production LLM evaluator on workflow YAML."""

from __future__ import annotations

from pathlib import Path

import pytest

from nimbusware_orchestrator.pipeline import make_dev_orchestrator
from nimbusware_orchestrator.workflow_agent_evaluator import (
    agent_evaluator_llm_branch_effective,
    agent_evaluator_production_default_on,
    parse_agent_evaluator_workflow_block,
)
from nimbusware_env import find_repo_root

ROOT = find_repo_root(start=Path(__file__).resolve().parents[1])


def test_production_default_on_nimbusware_production_profile() -> None:
    assert agent_evaluator_production_default_on(ROOT, "nimbusware_production") is True
    block = parse_agent_evaluator_workflow_block(ROOT, "nimbusware_production")
    assert agent_evaluator_llm_branch_effective(block) is True


def test_pipeline_agent_evaluator_production_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NIMBUSWARE_AGENT_EVALUATOR_LLM_STUB", raising=False)
    monkeypatch.delenv("NIMBUSWARE_USE_LLM", raising=False)
    orch, mem = make_dev_orchestrator(repo_root=ROOT)
    rid = orch.create_run("nimbusware_production")
    rows = mem.list_run_events(str(rid))
    created = next(r for r in rows if r["event_type"] == "run.created")
    ae = (created.get("metadata") or {}).get("agent_evaluator_effective") or {}
    assert ae.get("production_default_on") is True
    orch._maybe_emit_agent_evaluator_stage(rid)  # noqa: SLF001
    evs = mem.list_run_events(str(rid))
    stage = next(
        r for r in evs if (r.get("payload") or {}).get("stage_name", "").startswith("agent_eval")
    )
    meta = (stage.get("metadata") or {}).get("agent_evaluator") or {}
    assert meta.get("production_scoring_mode") in (
        "rules_derived",
        "llm",
        "rules",
    )
    assert meta.get("evaluation_branch") in ("rules", "rules_with_llm_policy")


def test_production_default_blocked_by_stub_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_AGENT_EVALUATOR_LLM_STUB", "1")
    assert agent_evaluator_production_default_on(ROOT, "nimbusware_production") is False

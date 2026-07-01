from __future__ import annotations

from pathlib import Path

import pytest

from nimbusware_env import find_repo_root
from nimbusware_orchestrator.escalation_policy_breadth import escalation_policy_breadth
from nimbusware_orchestrator.integration_adapter_scaffold import write_integration_adapter_scaffold
from nimbusware_orchestrator.security_scan import (
    SECURITY_SCAN_CATEGORIES,
    security_scan_tool_summary,
)
from nimbusware_orchestrator.workflow_agent_evaluator import (
    agent_evaluator_production_default_on,
)
from nimbusware_orchestrator.workflow_blocks_simple import (
    IntegrationAdapterWriterWorkflowBlock,
)
from nimbusware_orchestrator.workflow_self_refinement import (
    self_refinement_production_ungated_effective,
)
from nimbusware_orchestrator.workflow_universal_critique import (
    universal_critique_production_default_on,
)

ROOT = find_repo_root(start=Path(__file__).resolve().parents[1])


def test_write_integration_adapter_scaffold_files(tmp_path: Path) -> None:
    from uuid import uuid4

    rid = uuid4()
    block = IntegrationAdapterWriterWorkflowBlock(
        enabled=True,
        target_adapter_kind="api_bridge",
        stub_only=False,
    )
    out = write_integration_adapter_scaffold(tmp_path, rid, block)
    assert out["adapter_generation_status"] == "target_integrated"
    assert (tmp_path / out["adapter_module_path"]).is_file()
    assert (tmp_path / out["adapter_readme_path"]).is_file()


def test_agent_evaluator_production_default_on_profile() -> None:
    assert agent_evaluator_production_default_on(ROOT, "agent_evaluator_default_on") is True


def test_universal_critique_production_default_on_nimbusware_production() -> None:
    assert universal_critique_production_default_on(ROOT, "nimbusware_production") is True


def test_self_refinement_production_ungated_profile() -> None:
    assert (
        self_refinement_production_ungated_effective(
            ROOT,
            "self_refinement_production_ungated",
        )
        is True
    )


def test_security_scan_tool_summary() -> None:
    s = security_scan_tool_summary(1, 0)
    assert s["security_scan_categories"] == list(SECURITY_SCAN_CATEGORIES)
    assert s["security_scan_tools"]["ruff"] == 1


def test_escalation_policy_breadth() -> None:
    b = escalation_policy_breadth(ROOT)
    assert b["policy_path_exists"] is True
    assert isinstance(b["active_verification_triggers"], int)


def test_create_run_freezes_production_effective_metadata() -> None:
    from nimbusware_orchestrator.pipeline import make_dev_orchestrator

    orch, mem = make_dev_orchestrator(repo_root=ROOT)
    rid = orch.create_run("nimbusware_production")
    rows = mem.list_run_events(str(rid))
    created = next(r for r in rows if r["event_type"] == "run.created")
    meta = created.get("metadata") or {}
    assert meta["universal_critique_effective"]["production_default_on"] is True
    assert meta["agent_evaluator_effective"]["production_default_on"] is True


@pytest.mark.parametrize(
    "env_key,env_val",
    [
        ("NIMBUSWARE_AGENT_EVALUATOR_LLM_STUB", "1"),
        ("NIMBUSWARE_USE_LLM", "0"),
    ],
)
def test_agent_evaluator_production_default_kill_switch(
    env_key: str,
    env_val: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(env_key, env_val)
    assert agent_evaluator_production_default_on(ROOT, "agent_evaluator_default_on") is False

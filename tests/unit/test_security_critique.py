from __future__ import annotations

from pathlib import Path

from nimbusware_env import find_repo_root
from nimbusware_extensions.phase2 import UniversalCritiqueRouter
from nimbusware_orchestrator.pipeline import make_dev_orchestrator
from nimbusware_orchestrator.security_critique import (
    SECURITY_CRITIQUE_STAGE,
    emit_stub_security_critique_panel,
    run_security_scan_summary,
    security_critique_timeline_summary,
    security_scan_tools_failed,
)
from nimbusware_orchestrator.workflow_scan_critique import (
    SecurityCritiqueBlock,
    parse_security_critique_workflow_block,
    security_critique_effective,
)


def test_security_scan_tools_failed_detects_ruff() -> None:
    summary = {
        "security_scan_tools": {"ruff": 1, "bandit": 0, "mypy": 0},
    }
    failed, tools = security_scan_tools_failed(summary)
    assert failed
    assert "ruff" in tools


def test_security_critique_workflow_block() -> None:
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    block = parse_security_critique_workflow_block(root, "security_critique_on")
    assert block.enabled is True
    assert security_critique_effective(block)


def test_emit_stub_security_critique_panel_pass() -> None:
    repo = find_repo_root(start=Path(__file__).resolve().parents[1])
    orch, store = make_dev_orchestrator(repo)
    reg = orch._registry
    router = UniversalCritiqueRouter.from_yaml(
        repo / "configs" / "personas" / "critique_pairings.yaml",
    )
    run_id = orch.create_run("security_critique_on")
    clean = {
        "security_scan_tools": {"ruff": 0, "bandit": 0, "mypy": 0},
        "security_scan_exit": 0,
    }
    emit_stub_security_critique_panel(
        store,
        reg,
        router,
        run_id=run_id,
        producer_tax_key="backend_writer",
        scan_summary=clean,
        block=SecurityCritiqueBlock(enabled=True),
    )
    rows = store.list_run_events(str(run_id))
    stages = [
        (r.get("payload") or {}).get("stage_name")
        for r in rows
        if r.get("event_type") == "stage.started"
    ]
    assert SECURITY_CRITIQUE_STAGE in stages
    gates = [
        r
        for r in rows
        if r.get("event_type") == "gate.decision.emitted"
        and (r.get("payload") or {}).get("stage_name") == SECURITY_CRITIQUE_STAGE
    ]
    assert gates
    assert (gates[-1].get("payload") or {}).get("verdict") == "PASS"


def test_emit_stub_security_critique_panel_fail_on_dirty_scan() -> None:
    repo = find_repo_root(start=Path(__file__).resolve().parents[1])
    orch, store = make_dev_orchestrator(repo)
    reg = orch._registry
    router = UniversalCritiqueRouter.from_yaml(
        repo / "configs" / "personas" / "critique_pairings.yaml",
    )
    run_id = orch.create_run("security_critique_on")
    dirty = {
        "security_scan_tools": {"ruff": 2, "bandit": 0, "mypy": 0},
        "security_scan_exit": 2,
    }
    emit_stub_security_critique_panel(
        store,
        reg,
        router,
        run_id=run_id,
        producer_tax_key="backend_writer",
        scan_summary=dirty,
        block=SecurityCritiqueBlock(enabled=True, severity_floor="HIGH"),
        unanimous_gate_enforce=True,
    )
    rows = store.list_run_events(str(run_id))
    gates = [
        r
        for r in rows
        if r.get("event_type") == "gate.decision.emitted"
        and (r.get("payload") or {}).get("stage_name") == SECURITY_CRITIQUE_STAGE
    ]
    assert (gates[-1].get("payload") or {}).get("verdict") == "FAIL"
    events = [{"event_type": r.get("event_type"), "payload": r.get("payload")} for r in rows]
    summary = security_critique_timeline_summary(events)
    assert summary is not None
    assert summary["verdict"] == "FAIL"


def test_run_security_scan_summary_shape() -> None:
    repo = find_repo_root(start=Path(__file__).resolve().parents[1])
    summary = run_security_scan_summary(repo)
    assert "security_scan_tools" in summary

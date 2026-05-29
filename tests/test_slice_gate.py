"""Per-slice gate chain (fo153)."""

from __future__ import annotations

from hermes_orchestrator.micro_slice import parse_slice_plan
from hermes_orchestrator.slice_gate import map_paths_to_test_targets, run_slice_gate_chain


def test_slice_gate_chain_pass() -> None:
    plan = parse_slice_plan({"slice_id": "s1", "target_paths": ["packages/foo.py"]})
    result = run_slice_gate_chain(
        plan,
        verify_ok=True,
        critique_verdicts=["PASS"],
        tests_passed=True,
    )
    assert result.passed
    assert result.status == "completed"
    assert result.to_metadata()["slice_gate_verdict"] == "PASS"


def test_slice_gate_chain_blocks_on_verify_fail() -> None:
    plan = parse_slice_plan({"slice_id": "s2", "target_paths": []})
    result = run_slice_gate_chain(plan, verify_ok=False, critique_verdicts=["PASS"])
    assert not result.passed
    assert result.status == "blocked"


def test_map_paths_to_test_targets() -> None:
    targets = map_paths_to_test_targets(("packages/hermes_api/app.py",))
    assert any("test_" in t for t in targets)

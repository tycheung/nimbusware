from __future__ import annotations

from nimbusware_orchestrator.micro_slice import SlicePlan
from nimbusware_orchestrator.slice_gate import run_slice_gate_chain


def test_slice_gate_resolution_accord_passes_remediable_critique_fail() -> None:
    plan = SlicePlan(
        slice_id="s1",
        target_paths=("src/a.py",),
        rationale="test",
        acceptance_criteria=("ok",),
    )
    result = run_slice_gate_chain(
        plan,
        verify_ok=True,
        critique_verdicts=["style:FAIL"],
        tests_passed=True,
        autopilot_level=6,
    )
    assert result.passed is True
    critique = next(s for s in result.steps if s.name == "slice.critique")
    assert critique.verdict == "PASS"
    assert "resolution=" in critique.detail


def test_slice_gate_resolution_hard_block_still_fails() -> None:
    plan = SlicePlan(
        slice_id="s2",
        target_paths=("src/a.py",),
        rationale="test",
        acceptance_criteria=("ok",),
    )
    result = run_slice_gate_chain(
        plan,
        verify_ok=True,
        critique_verdicts=["injection:FAIL"],
        tests_passed=True,
    )
    assert result.passed is False

from __future__ import annotations

from orchestrator.profiles.enforcement_profiles import resolve_enforcement_profile
from orchestrator.slice.gate import map_paths_to_test_targets, run_slice_gate_chain
from orchestrator.slice.micro_slice import parse_slice_plan


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
    targets = map_paths_to_test_targets(("packages/api/app.py",))
    assert any("test_" in t for t in targets)


def test_slice_gate_skip_becomes_fail_with_enforcement() -> None:
    plan = parse_slice_plan({"slice_id": "s3", "target_paths": ["packages/foo.py"]})
    profile = resolve_enforcement_profile(level=6)
    result = run_slice_gate_chain(
        plan,
        verify_ok=True,
        critique_verdicts=["PASS"],
        tests_passed=None,
        enforcement_profile=profile,
    )
    assert not result.passed
    test_step = next(s for s in result.steps if s.name == "slice.test")
    assert test_step.verdict == "FAIL"

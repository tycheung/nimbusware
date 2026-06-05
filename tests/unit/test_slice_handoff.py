from __future__ import annotations

from agent_core.models.slice_handoff import SliceHandoffSummary
from nimbusware_orchestrator.micro_slice import parse_slice_plan
from nimbusware_orchestrator.slice_gate import SliceGateChainResult, SliceGateStep
from nimbusware_orchestrator.slice_handoff import (
    build_slice_handoff_summary,
    handoff_markdown_capped,
    latest_handoff_from_events,
)


def _plan(sid: str) -> object:
    return parse_slice_plan(
        {
            "slice_id": sid,
            "target_paths": [f"packages/demo/{sid}.py"],
            "rationale": f"work on {sid}",
        },
    )


def _gate(passed: bool, *, slice_id: str = "slice-x") -> SliceGateChainResult:
    verdict = "PASS" if passed else "FAIL"
    return SliceGateChainResult(
        slice_id=slice_id,
        passed=passed,
        steps=(SliceGateStep(name="verify", verdict=verdict),),
        status="passed" if passed else "blocked",
    )


def test_handoff_merge_three_slices() -> None:
    h1 = build_slice_handoff_summary(
        _plan("slice-1"),
        gate=_gate(True, slice_id="slice-1"),
        diff_stat="2 lines",
    )
    h2 = build_slice_handoff_summary(
        _plan("slice-2"),
        prior=h1,
        gate=_gate(True, slice_id="slice-2"),
        paths_touched=("packages/demo/extra.py",),
        diff_stat="4 lines",
    )
    h3 = build_slice_handoff_summary(
        _plan("slice-3"),
        prior=h2,
        gate=_gate(False, slice_id="slice-3"),
        diff_stat="0 lines",
    )
    assert len(h3.progress) == 3
    assert "slice-3: failed" in h3.progress[-1]
    assert "packages/demo/extra.py" in h3.modified_files
    md = handoff_markdown_capped(h3)
    assert "<modified-files>" in md
    assert "slice-3" in md


def test_handoff_fail_updates_next_steps() -> None:
    summary = build_slice_handoff_summary(
        _plan("slice-2"),
        gate=_gate(False, slice_id="slice-2"),
    )
    assert any("failure" in step.lower() for step in summary.next_steps)


def test_latest_handoff_from_events() -> None:
    events = [
        {
            "payload": {"stage_name": "slice.handoff"},
            "metadata": {
                "slice_handoff": SliceHandoffSummary(goal="g", progress=("a",)).model_dump(),
            },
        },
    ]
    got = latest_handoff_from_events(events)
    assert got is not None
    assert got.goal == "g"

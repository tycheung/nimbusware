from __future__ import annotations

from agent_core.models.backlog import (
    BacklogEpic,
    BacklogFeature,
    BacklogMetadata,
    BacklogSlice,
    DeliveryBacklog,
    EpicStatus,
    SliceStatus,
    sync_backlog_metadata,
)
from orchestrator.campaign.failure_escalate import (
    decide_escalation,
    escalation_depth,
    revise_backlog_with_replan,
    slice_gate_fail_streak,
    walk_dependency_back,
)
from orchestrator.campaign.slice_selector import select_next_slice


def _gate(slice_id: str, verdict: str) -> dict:
    return {
        "event_type": "stage.passed" if verdict == "PASS" else "stage.failed",
        "payload": {"stage_name": "slice.gate"},
        "metadata": {
            "backlog_slice_id": slice_id,
            "slice_gate_verdict": verdict,
        },
    }


def _chain_backlog() -> DeliveryBacklog:
    return sync_backlog_metadata(
        DeliveryBacklog(
            campaign_id="00000000-0000-4000-8000-000000000099",
            metadata=BacklogMetadata(total_slices_planned=3, slices_completed=1),
            epics=(
                BacklogEpic(
                    epic_id="epic-1",
                    title="Demo",
                    status=EpicStatus.IN_PROGRESS,
                    features=(
                        BacklogFeature(
                            feature_id="feat-1",
                            title="Demo feature",
                            acceptance_criteria=("ok",),
                            slices=(
                                BacklogSlice(
                                    slice_id="slice-a",
                                    status=SliceStatus.PASSED,
                                    rationale="root",
                                    target_paths=("a.py",),
                                ),
                                BacklogSlice(
                                    slice_id="slice-b",
                                    status=SliceStatus.PASSED,
                                    rationale="mid",
                                    target_paths=("b.py",),
                                    depends_on=("slice-a",),
                                ),
                                BacklogSlice(
                                    slice_id="slice-c",
                                    status=SliceStatus.FAILED,
                                    rationale="head",
                                    target_paths=("c.py",),
                                    depends_on=("slice-b",),
                                ),
                            ),
                        ),
                    ),
                ),
            ),
        )
    )


def test_escalation_depth_steps_every_two_fails() -> None:
    assert escalation_depth(1) == 0
    assert escalation_depth(2) == 1
    assert escalation_depth(3) == 1
    assert escalation_depth(4) == 2


def test_walk_dependency_back() -> None:
    graph = {
        "slice-c": ("slice-b",),
        "slice-b": ("slice-a",),
        "slice-a": (),
    }
    assert walk_dependency_back(graph, "slice-c", 0) == "slice-c"
    assert walk_dependency_back(graph, "slice-c", 1) == "slice-b"
    assert walk_dependency_back(graph, "slice-c", 2) == "slice-a"
    assert walk_dependency_back(graph, "slice-c", 9) == "slice-a"


def test_decide_escalation_retries_same_then_ancestor() -> None:
    backlog = _chain_backlog()
    one_fail = [_gate("slice-c", "FAIL")]
    d0 = decide_escalation(backlog, one_fail)
    assert d0 is not None
    assert d0.slice_id == "slice-c"
    assert d0.needs_replan is False

    two_fail = [_gate("slice-c", "FAIL"), _gate("slice-c", "FAIL")]
    d1 = decide_escalation(backlog, two_fail)
    assert d1 is not None
    assert d1.slice_id == "slice-b"
    assert d1.depth == 1


def test_decide_escalation_needs_replan_past_root() -> None:
    backlog = _chain_backlog()
    # chain depth 2 (c→b→a); depth 3 requires replan
    rows = [_gate("slice-c", "FAIL")] * 6
    assert slice_gate_fail_streak(rows, "slice-c") == 6
    d = decide_escalation(backlog, rows)
    assert d is not None
    assert d.needs_replan is True
    assert d.failed_slice_id == "slice-c"


def test_revise_backlog_with_replan_prepends_slice() -> None:
    backlog = _chain_backlog()
    revised = revise_backlog_with_replan(backlog, failed_slice_id="slice-c", fail_streak=6)
    slices = {s.slice_id: s for e in revised.epics for f in e.features for s in f.slices}
    assert "replan-slice-c-6" in slices
    assert slices["replan-slice-c-6"].status == SliceStatus.PENDING
    assert "replan-slice-c-6" in slices["slice-c"].depends_on


def test_select_next_slice_uses_escalation_rows() -> None:
    backlog = _chain_backlog()
    rows = [_gate("slice-c", "FAIL"), _gate("slice-c", "FAIL")]
    selected = select_next_slice(backlog, rows=rows)
    assert selected is not None
    assert selected.slice.slice_id == "slice-b"

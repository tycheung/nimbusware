from __future__ import annotations

from uuid import uuid4

from nimbusware_orchestrator.autopilot_profiles import (
    autopilot_profile_from_rows,
    resolve_autopilot_profile,
)
from nimbusware_orchestrator.interjection_queue import InterjectionPriority, queue_for_run
from nimbusware_orchestrator.micro_slice import SlicePlan
from nimbusware_orchestrator.slice_cycle_integration import (
    apply_interjection_to_plan,
    apply_operator_pause,
    gate_result_for_force_break,
    merge_pre_gate_into_verify,
    process_interjection_cycle,
)
from nimbusware_store.memory import InMemoryEventStore


def test_autopilot_profile_from_run_metadata() -> None:
    rows = [
        {
            "event_type": "run.created",
            "metadata": {"autopilot_effective": {"level": 3, "checkpoints": ["stop_on_gate_fail"]}},
        },
    ]
    profile = autopilot_profile_from_rows(rows)
    assert profile.level == 3
    assert profile.should_stop("stop_on_gate_fail")


def test_interjection_drain_and_apply_to_plan() -> None:
    run_id = str(uuid4())
    store = InMemoryEventStore()
    q = queue_for_run(run_id)
    q.enqueue("fix auth", priority=InterjectionPriority.LAST)
    q.enqueue("urgent", priority=InterjectionPriority.NEXT)
    cycle = process_interjection_cycle(store, run_id)
    assert len(cycle.items) == 2
    assert cycle.messages[0] == "urgent"
    plan = SlicePlan(
        slice_id="s1",
        target_paths=("a.py",),
        rationale="base",
        acceptance_criteria=("ok",),
    )
    updated = apply_interjection_to_plan(plan, cycle)
    assert "Operator interjection" in updated.rationale
    assert "urgent" in updated.rationale


def test_force_break_gate_result() -> None:
    plan = SlicePlan(
        slice_id="s2",
        target_paths=("a.py",),
        rationale="base",
        acceptance_criteria=("ok",),
    )
    gate = gate_result_for_force_break(plan)
    assert gate.passed is False
    assert gate.status == "paused_for_operator"


def test_operator_pause_on_gate_fail() -> None:
    profile = resolve_autopilot_profile(level=0)
    gate = gate_result_for_force_break(
        SlicePlan("s3", ("a.py",), "r", ("ok",)),
    )
    paused = apply_operator_pause(gate, profile)
    assert paused.status == "paused_for_operator"
    assert any(s.name == "autopilot.pause" for s in paused.steps)


def test_merge_pre_gate_regression_failures() -> None:
    from nimbusware_orchestrator.slice_cycle_integration import PreGateRegression

    ok, log = merge_pre_gate_into_verify(
        True,
        "clean",
        PreGateRegression(http_passed=False, http_detail="regression_detected"),
    )
    assert ok is False
    assert "dev_env.regression" in log

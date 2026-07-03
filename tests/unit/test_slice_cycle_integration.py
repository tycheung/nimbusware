from __future__ import annotations

from uuid import uuid4

from orchestrator.autopilot_profiles import (
    autopilot_profile_from_rows,
    persist_run_autopilot,
    resolve_autopilot_profile,
)
from orchestrator.interjection_queue import InterjectionPriority, queue_for_run
from orchestrator.micro_slice import SlicePlan
from orchestrator.slice_cycle_integration import (
    apply_operator_pause,
    merge_pre_gate_into_verify,
)
from orchestrator.slice_interjection import (
    apply_interjection_to_plan,
    gate_result_for_force_break,
    process_interjection_cycle,
)
from store.memory import InMemoryEventStore


def test_autopilot_persist_and_reload_from_events() -> None:
    store = InMemoryEventStore()
    run_id = uuid4()
    profile = resolve_autopilot_profile(
        level=7,
        custom_checkpoints={"stop_on_gate_fail", "stop_at_terminal_review"},
    )
    persist_run_autopilot(store, run_id, profile)
    rows = store.list_run_events(str(run_id))
    reloaded = autopilot_profile_from_rows(rows)
    assert reloaded.level == 7
    assert reloaded.should_stop("stop_on_gate_fail")
    assert reloaded.custom is True


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


def test_latest_learning_excerpt_from_diagnose_event() -> None:
    from orchestrator.diagnose_learn import latest_learning_excerpt_from_rows

    rows = [
        {
            "payload": {"stage_name": "diagnose.learn"},
            "metadata": {
                "diagnose_learn": {
                    "learning_path": "missing.md",
                    "excerpt": "Root cause: missing import",
                },
            },
        },
    ]
    assert "missing import" in latest_learning_excerpt_from_rows(rows)


def test_theater_visibility_filters_low_autopilot() -> None:
    from orchestrator.autopilot_profiles import filter_theater_messages_for_autopilot

    messages = [
        {"severity": "info", "message_kind": "system", "headline": "a"},
        {"severity": "block", "message_kind": "slice", "headline": "b"},
    ]
    filtered = filter_theater_messages_for_autopilot(messages, level=10)
    assert len(filtered) == 1
    assert filtered[0]["headline"] == "b"


def test_dev_env_milestone_gating() -> None:
    from orchestrator.dev_env_milestones import (
        dev_env_auto_start_enabled,
        dev_env_http_regression_enabled,
    )

    profile_rows = [
        {
            "event_type": "run.created",
            "metadata": {
                "campaign_effective": {
                    "enabled": True,
                    "workflow_profile": "micro_slice_web",
                    "persistent_dev_env": {"enabled": True},
                },
            },
        },
    ]
    assert dev_env_auto_start_enabled(profile_rows) is False
    assert dev_env_http_regression_enabled(profile_rows) is False
    passed_rows = profile_rows + [
        {
            "event_type": "stage.passed",
            "payload": {"stage_name": "slice.test"},
        },
    ]
    assert dev_env_auto_start_enabled(passed_rows) is True


def test_merge_pre_gate_regression_failures() -> None:
    from orchestrator.slice_cycle_integration import PreGateRegression

    ok, log = merge_pre_gate_into_verify(
        True,
        "clean",
        PreGateRegression(http_passed=False, http_detail="regression_detected"),
    )
    assert ok is False
    assert "dev_env.regression" in log

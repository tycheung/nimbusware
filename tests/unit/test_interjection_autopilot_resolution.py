from __future__ import annotations

from orchestrator.improvement.resolution_council import (
    aggregate_resolution_soak_metrics,
    classify_hard_block,
    run_resolution_council,
)
from orchestrator.interjection_queue import InterjectionPriority, queue_for_run
from orchestrator.profiles.autopilot_profiles import preset_for_level, resolve_autopilot_profile


def test_interjection_queue_next_before_last() -> None:
    q = queue_for_run("run-a")
    q.enqueue("last item", priority=InterjectionPriority.LAST)
    q.enqueue("next item", priority=InterjectionPriority.NEXT)
    drained = q.drain()
    assert drained[0].message == "next item"
    assert drained[1].message == "last item"


def test_autopilot_preset_levels() -> None:
    low = preset_for_level(0)
    high = preset_for_level(10)
    assert len(low.checkpoints) > len(high.checkpoints)
    custom = resolve_autopilot_profile(custom_checkpoints={"stop_on_gate_fail"})
    assert custom.custom is True


def test_default_autopilot_level_for_work_type() -> None:
    from orchestrator.profiles.autopilot_profiles import (
        autopilot_effective_metadata,
        default_autopilot_level_for_work_type,
    )

    assert default_autopilot_level_for_work_type("patch") == 8
    assert default_autopilot_level_for_work_type("factory") == 10
    assert default_autopilot_level_for_work_type("slice") == 5
    meta = autopilot_effective_metadata("patch")
    assert meta["level"] == 8
    assert meta["source"] == "work_type_default"


def test_resolution_council_hard_block() -> None:
    result = run_resolution_council(
        findings=[{"kind": "injection", "message": "sql injection", "severity": "security_p0"}],
        autopilot_level=10,
    )
    assert result.verdict.hard_block is True


def test_resolution_council_accord_at_high_autopilot() -> None:
    result = run_resolution_council(
        findings=[{"kind": "style", "message": "naming", "severity": "info"}],
        autopilot_level=8,
    )
    assert result.verdict.hard_block is False
    assert result.verdict.accord is True


def test_classify_hard_block() -> None:
    assert classify_hard_block("auth_bypass") is True
    assert classify_hard_block("style") is False


def test_resolution_council_emits_soak_metrics() -> None:
    result = run_resolution_council(
        findings=[{"kind": "style", "message": "naming", "severity": "info"}],
        autopilot_level=4,
    )
    assert result.soak is not None
    block = result.to_dict()
    assert block["soak"]["finding_count"] == 1
    assert block["soak"]["debate_first"] is True


def test_aggregate_resolution_soak_metrics() -> None:
    rows = [
        {
            "metadata": {
                "resolution_council": {
                    "soak": {"debate_first": True, "accord": False, "hard_block": False},
                },
            },
        },
        {
            "metadata": {
                "resolution_council": {
                    "soak": {"debate_first": False, "accord": True, "hard_block": False},
                },
            },
        },
    ]
    agg = aggregate_resolution_soak_metrics(rows)
    assert agg["resolution_council_runs"] == 2
    assert agg["debate_first_rate"] == 0.5
    assert agg["accord_rate"] == 0.5

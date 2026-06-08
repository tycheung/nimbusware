from __future__ import annotations

from nimbusware_orchestrator.autopilot_profiles import preset_for_level, resolve_autopilot_profile
from nimbusware_orchestrator.interjection_queue import InterjectionPriority, queue_for_run
from nimbusware_orchestrator.resolution_council import classify_hard_block, run_resolution_council


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

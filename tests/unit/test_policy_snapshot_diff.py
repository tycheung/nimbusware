from __future__ import annotations

from hermes_orchestrator.policy_snapshot_diff import diff_policy_snapshots


def test_diff_policy_snapshots_detects_change() -> None:
    out = diff_policy_snapshots({"a": 1}, {"a": 2})
    assert out["identical"] is False
    assert out["changed_count"] == 1
    assert out["changed"][0]["key"] == "a"

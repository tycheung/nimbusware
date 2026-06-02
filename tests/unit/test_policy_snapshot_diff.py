from __future__ import annotations

from hermes_orchestrator.policy_snapshot_diff import diff_policy_snapshots


def test_diff_policy_snapshots_detects_change() -> None:
    diff = diff_policy_snapshots(
        {"network_egress_domain_count": 1},
        {"network_egress_domain_count": 2},
    )
    assert diff["identical"] is False
    assert diff["changed_count"] == 1

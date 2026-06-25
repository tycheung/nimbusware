from __future__ import annotations

from pathlib import Path

from nimbusware_maker.workspace_readiness import assess_workspace_readiness
from nimbusware_orchestrator.fleet_slice_policy import tenant_slice_policy


def test_tenant_slice_policy_default() -> None:
    pol = tenant_slice_policy("default")
    assert pol.max_files == 3
    assert pol.slice_budget_preset == "standard"


def test_workspace_readiness_missing_path(tmp_path: Path) -> None:
    missing = tmp_path / "nope"
    body = assess_workspace_readiness(missing)
    assert body["ready"] is False
    assert body["blockers"]

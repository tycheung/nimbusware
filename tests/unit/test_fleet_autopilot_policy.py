from __future__ import annotations

from pathlib import Path

from orchestrator.fleet.policies import (
    FleetAutopilotPolicy,
    load_fleet_autopilot_policies,
    save_fleet_autopilot_policies,
    tenant_autopilot_policy,
)
from orchestrator.fleet.policy_guards import (
    clamp_autopilot_profile_to_policy as clamp_profile_to_policy,
)
from orchestrator.profiles.autopilot_profiles import resolve_autopilot_profile


def test_tenant_policy_clamps_level_and_adds_checkpoints(tmp_path: Path) -> None:
    ent = tmp_path / "configs" / "enterprise"
    ent.mkdir(parents=True)
    (ent / "fleet_autopilot_policies.yaml").write_text(
        "version: 1\ntenants:\n  ops:\n    max_autopilot_level: 6\n"
        "    required_checkpoints:\n      - stop_on_gate_fail\n",
        encoding="utf-8",
    )
    policies = load_fleet_autopilot_policies(tmp_path)
    assert "ops" in policies
    policy = policies["ops"]
    profile = resolve_autopilot_profile(level=9)
    clamped = clamp_profile_to_policy(profile, policy)
    assert clamped.level == 6
    assert "stop_on_gate_fail" in clamped.checkpoints


def test_save_and_load_round_trip(tmp_path: Path) -> None:
    (tmp_path / "configs" / "enterprise").mkdir(parents=True)
    policy = FleetAutopilotPolicy(
        tenant_slug="acme",
        max_autopilot_level=7,
        required_checkpoints=frozenset({"stop_at_terminal_review"}),
    )
    save_fleet_autopilot_policies({"acme": policy}, repo_root=tmp_path)
    loaded = tenant_autopilot_policy("acme", repo_root=tmp_path)
    assert loaded.max_autopilot_level == 7
    assert "stop_at_terminal_review" in loaded.required_checkpoints

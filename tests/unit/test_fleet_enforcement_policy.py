from __future__ import annotations

from orchestrator.fleet.policies import (
    FleetEnforcementPolicy,
    load_fleet_enforcement_policies,
    save_fleet_enforcement_policies,
)
from orchestrator.fleet.policy_guards import (
    clamp_enforcement_profile_to_policy as clamp_profile_to_policy,
)
from orchestrator.profiles.enforcement_profiles import preset_for_enforcement_level


def test_clamp_profile_to_policy(tmp_path) -> None:
    policy = FleetEnforcementPolicy("ops", min_enforcement_level=6, max_enforcement_level=8)
    profile = preset_for_enforcement_level(10)
    clamped = clamp_profile_to_policy(profile, policy)
    assert clamped.level == 8


def test_fleet_enforcement_policies_round_trip(tmp_path) -> None:
    path = tmp_path / "configs" / "enterprise" / "fleet_enforcement_policies.yaml"
    path.parent.mkdir(parents=True)
    path.write_text(
        "version: 1\ntenants:\n  ops:\n    min_enforcement_level: 5\n    max_enforcement_level: 9\n",
        encoding="utf-8",
    )
    policies = load_fleet_enforcement_policies(tmp_path)
    assert policies["ops"].min_enforcement_level == 5
    save_fleet_enforcement_policies(policies, repo_root=tmp_path)
    reloaded = load_fleet_enforcement_policies(tmp_path)
    assert reloaded["ops"].max_enforcement_level == 9

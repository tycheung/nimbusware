from __future__ import annotations

from orchestrator.fleet_policies import (
    FleetDiscoveryPolicy,
    load_fleet_discovery_policies,
    save_fleet_discovery_policies,
    tenant_discovery_policy,
)


def test_fleet_discovery_policies_round_trip(tmp_path) -> None:
    path = tmp_path / "configs" / "enterprise" / "fleet_discovery_policies.yaml"
    path.parent.mkdir(parents=True)
    path.write_text(
        "version: 1\ntenants:\n  default:\n    discovery_required_fields: []\n",
        encoding="utf-8",
    )
    policies = load_fleet_discovery_policies(tmp_path)
    policies["regulated"] = FleetDiscoveryPolicy(
        tenant_slug="regulated",
        discovery_required_fields=("hosting", "data_residency"),
    )
    save_fleet_discovery_policies(policies, repo_root=tmp_path)
    reloaded = load_fleet_discovery_policies(tmp_path)
    assert reloaded["regulated"].discovery_required_fields == ("hosting", "data_residency")


def test_tenant_discovery_policy_falls_back_to_default(tmp_path) -> None:
    path = tmp_path / "configs" / "enterprise" / "fleet_discovery_policies.yaml"
    path.parent.mkdir(parents=True)
    path.write_text(
        "version: 1\ntenants:\n  default:\n    discovery_required_fields:\n      - hosting\n",
        encoding="utf-8",
    )
    policy = tenant_discovery_policy("unknown-tenant", repo_root=tmp_path)
    assert policy.discovery_required_fields == ("hosting",)

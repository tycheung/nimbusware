from __future__ import annotations

from orchestrator.fleet_policies import (
    FleetDeployPolicy,
    load_fleet_deploy_policies,
    save_fleet_deploy_policies,
    tenant_deploy_policy,
)


def test_fleet_deploy_policies_round_trip(tmp_path) -> None:
    path = tmp_path / "configs" / "enterprise" / "fleet_deploy_policies.yaml"
    path.parent.mkdir(parents=True)
    path.write_text(
        "version: 1\ntenants:\n  default:\n    allowed_deploy_targets:\n      - aws-ecs\n",
        encoding="utf-8",
    )
    policies = load_fleet_deploy_policies(tmp_path)
    assert "default" in policies
    policies["strict"] = FleetDeployPolicy(
        tenant_slug="strict",
        allowed_deploy_targets=("aws-static-site",),
    )
    save_fleet_deploy_policies(policies, repo_root=tmp_path)
    reloaded = load_fleet_deploy_policies(tmp_path)
    assert reloaded["strict"].allowed_deploy_targets == ("aws-static-site",)


def test_tenant_deploy_policy_falls_back_to_default(tmp_path) -> None:
    path = tmp_path / "configs" / "enterprise" / "fleet_deploy_policies.yaml"
    path.parent.mkdir(parents=True)
    path.write_text(
        "version: 1\ntenants:\n  default:\n    allowed_deploy_targets:\n      - github-actions\n",
        encoding="utf-8",
    )
    policy = tenant_deploy_policy("unknown-tenant", repo_root=tmp_path)
    assert policy.allowed_deploy_targets == ("github-actions",)

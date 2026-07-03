from __future__ import annotations

from pathlib import Path

import yaml

from nimbusware_orchestrator.fleet_policies import (
    FleetDeployPolicy,
    load_fleet_deploy_policies,
    save_fleet_deploy_policies,
    tenant_deploy_policy,
)
from nimbusware_orchestrator.fleet_policy_loader import (
    enterprise_policies_path,
    load_tenant_policies,
    save_tenant_policies,
    tenant_policy,
)


def test_fleet_policy_loader_round_trip(tmp_path: Path) -> None:
    yaml_path = enterprise_policies_path("fleet_deploy_policies.yaml", tmp_path)
    yaml_path.parent.mkdir(parents=True, exist_ok=True)
    yaml_path.write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "tenants": {
                    "acme": {"allowed_deploy_targets": ["github-actions"]},
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    policies = load_fleet_deploy_policies(tmp_path)
    assert "acme" in policies
    assert policies["acme"].allowed_deploy_targets == ("github-actions",)

    policies["acme"] = FleetDeployPolicy(
        tenant_slug="acme",
        allowed_deploy_targets=("aws-ecs",),
    )
    save_fleet_deploy_policies(policies, repo_root=tmp_path)
    reloaded = load_fleet_deploy_policies(tmp_path)
    assert reloaded["acme"].allowed_deploy_targets == ("aws-ecs",)

    resolved = tenant_deploy_policy("missing", repo_root=tmp_path)
    assert resolved.tenant_slug == "missing"


def test_fleet_policy_loader_generic_api(tmp_path: Path) -> None:
    def _parse(slug: str, entry: dict) -> FleetDeployPolicy:
        return FleetDeployPolicy(tenant_slug=slug, allowed_deploy_targets=("github-actions",))

    def _serialize(policy: FleetDeployPolicy) -> dict:
        return {"allowed_deploy_targets": list(policy.allowed_deploy_targets)}

    loaded = load_tenant_policies("fleet_deploy_policies.yaml", _parse, repo_root=tmp_path)
    assert loaded == {}

    save_tenant_policies(
        "fleet_deploy_policies.yaml",
        {"t1": FleetDeployPolicy(tenant_slug="t1")},
        _serialize,
        repo_root=tmp_path,
    )
    assert enterprise_policies_path("fleet_deploy_policies.yaml", tmp_path).is_file()

    picked = tenant_policy(
        "t1",
        lambda repo_root=None: load_tenant_policies(
            "fleet_deploy_policies.yaml",
            _parse,
            repo_root=repo_root,
        ),
        FleetDeployPolicy,
        repo_root=tmp_path,
    )
    assert picked.tenant_slug == "t1"

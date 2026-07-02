from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from nimbusware_orchestrator.fleet_policy_loader import (
    load_tenant_policies,
    save_tenant_policies,
    tenant_policy,
)

DEFAULT_ENTERPRISE_DEPLOY_TARGETS: tuple[str, ...] = (
    "aws-ecs",
    "aws-static-site",
    "github-actions",
)

_YAML = "fleet_deploy_policies.yaml"


@dataclass(frozen=True)
class FleetDeployPolicy:
    tenant_slug: str
    allowed_deploy_targets: tuple[str, ...] = DEFAULT_ENTERPRISE_DEPLOY_TARGETS

    def to_dict(self) -> dict[str, Any]:
        return {
            "tenant_slug": self.tenant_slug,
            "allowed_deploy_targets": list(self.allowed_deploy_targets),
        }


def _normalize_targets(raw: Any) -> tuple[str, ...]:
    if not isinstance(raw, list):
        return DEFAULT_ENTERPRISE_DEPLOY_TARGETS
    out = tuple(str(item).strip() for item in raw if str(item).strip())
    return out or DEFAULT_ENTERPRISE_DEPLOY_TARGETS


def _parse_entry(slug: str, entry: dict[str, Any]) -> FleetDeployPolicy:
    return FleetDeployPolicy(
        tenant_slug=slug,
        allowed_deploy_targets=_normalize_targets(entry.get("allowed_deploy_targets")),
    )


def _serialize_entry(policy: FleetDeployPolicy) -> dict[str, Any]:
    return {"allowed_deploy_targets": list(policy.allowed_deploy_targets)}


def load_fleet_deploy_policies(
    repo_root: Path | None = None,
) -> dict[str, FleetDeployPolicy]:
    return load_tenant_policies(_YAML, _parse_entry, repo_root=repo_root)


def save_fleet_deploy_policies(
    policies: dict[str, FleetDeployPolicy],
    *,
    repo_root: Path | None = None,
) -> None:
    save_tenant_policies(_YAML, policies, _serialize_entry, repo_root=repo_root)


def tenant_deploy_policy(
    tenant_slug: str | None,
    *,
    repo_root: Path | None = None,
) -> FleetDeployPolicy:
    return tenant_policy(
        tenant_slug,
        load_fleet_deploy_policies,
        FleetDeployPolicy,
        repo_root=repo_root,
    )

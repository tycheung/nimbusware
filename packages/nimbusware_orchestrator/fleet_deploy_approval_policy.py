from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from nimbusware_orchestrator.fleet_policy_loader import (
    load_tenant_policies,
    save_tenant_policies,
    tenant_policy,
)

DeployApprovalChain = Literal["maker_only", "session_admin", "dual_control"]
VALID_DEPLOY_APPROVAL_CHAINS = frozenset({"maker_only", "session_admin", "dual_control"})

_YAML = "fleet_deploy_approval_policies.yaml"


@dataclass(frozen=True)
class FleetDeployApprovalPolicy:
    tenant_slug: str
    deploy_approval_chain: DeployApprovalChain = "maker_only"

    def to_dict(self) -> dict[str, Any]:
        return {
            "tenant_slug": self.tenant_slug,
            "deploy_approval_chain": self.deploy_approval_chain,
        }


def _parse_entry(slug: str, entry: dict[str, Any]) -> FleetDeployApprovalPolicy:
    chain = str(entry.get("deploy_approval_chain") or "maker_only").strip()
    if chain not in VALID_DEPLOY_APPROVAL_CHAINS:
        chain = "maker_only"
    return FleetDeployApprovalPolicy(
        tenant_slug=slug,
        deploy_approval_chain=chain,  # type: ignore[arg-type]
    )


def _serialize_entry(policy: FleetDeployApprovalPolicy) -> dict[str, Any]:
    return {"deploy_approval_chain": policy.deploy_approval_chain}


def load_fleet_deploy_approval_policies(
    repo_root: Path | None = None,
) -> dict[str, FleetDeployApprovalPolicy]:
    return load_tenant_policies(_YAML, _parse_entry, repo_root=repo_root)


def save_fleet_deploy_approval_policies(
    policies: dict[str, FleetDeployApprovalPolicy],
    *,
    repo_root: Path | None = None,
) -> None:
    save_tenant_policies(_YAML, policies, _serialize_entry, repo_root=repo_root)


def tenant_deploy_approval_policy(
    tenant_slug: str | None,
    *,
    repo_root: Path | None = None,
) -> FleetDeployApprovalPolicy:
    return tenant_policy(
        tenant_slug,
        load_fleet_deploy_approval_policies,
        FleetDeployApprovalPolicy,
        repo_root=repo_root,
    )

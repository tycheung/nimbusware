from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml

from agent_core.mapping import mapping_or_empty
from nimbusware_env import find_repo_root
from nimbusware_iam.constants import DEFAULT_TENANT_SLUG

DeployApprovalChain = Literal["maker_only", "session_admin", "dual_control"]
VALID_DEPLOY_APPROVAL_CHAINS = frozenset({"maker_only", "session_admin", "dual_control"})


@dataclass(frozen=True)
class FleetDeployApprovalPolicy:
    tenant_slug: str
    deploy_approval_chain: DeployApprovalChain = "maker_only"

    def to_dict(self) -> dict[str, Any]:
        return {
            "tenant_slug": self.tenant_slug,
            "deploy_approval_chain": self.deploy_approval_chain,
        }


def _policies_path(repo_root: Path | None = None) -> Path:
    root = repo_root or find_repo_root()
    return root / "configs" / "enterprise" / "fleet_deploy_approval_policies.yaml"


def load_fleet_deploy_approval_policies(
    repo_root: Path | None = None,
) -> dict[str, FleetDeployApprovalPolicy]:
    path = _policies_path(repo_root)
    if not path.is_file():
        return {}
    raw = mapping_or_empty(yaml.safe_load(path.read_text(encoding="utf-8")))
    tenants = mapping_or_empty(raw.get("tenants"))
    out: dict[str, FleetDeployApprovalPolicy] = {}
    for slug, entry in tenants.items():
        if not isinstance(entry, dict):
            continue
        slug_s = str(slug).strip()
        if not slug_s:
            continue
        chain = str(entry.get("deploy_approval_chain") or "maker_only").strip()
        if chain not in VALID_DEPLOY_APPROVAL_CHAINS:
            chain = "maker_only"
        out[slug_s] = FleetDeployApprovalPolicy(
            tenant_slug=slug_s,
            deploy_approval_chain=chain,  # type: ignore[arg-type]
        )
    return out


def save_fleet_deploy_approval_policies(
    policies: dict[str, FleetDeployApprovalPolicy],
    *,
    repo_root: Path | None = None,
) -> None:
    path = _policies_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    tenants = {
        slug: {"deploy_approval_chain": p.deploy_approval_chain}
        for slug, p in sorted(policies.items(), key=lambda x: x[0])
    }
    payload = {"version": 1, "tenants": tenants}
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def tenant_deploy_approval_policy(
    tenant_slug: str | None,
    *,
    repo_root: Path | None = None,
) -> FleetDeployApprovalPolicy:
    slug = (tenant_slug or DEFAULT_TENANT_SLUG).strip() or DEFAULT_TENANT_SLUG
    policies = load_fleet_deploy_approval_policies(repo_root)
    if slug in policies:
        return policies[slug]
    if DEFAULT_TENANT_SLUG in policies:
        return policies[DEFAULT_TENANT_SLUG]
    return FleetDeployApprovalPolicy(tenant_slug=slug)

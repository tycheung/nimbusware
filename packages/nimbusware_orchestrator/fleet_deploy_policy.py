from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from agent_core.mapping import mapping_or_empty
from nimbusware_env import find_repo_root
from nimbusware_iam.constants import DEFAULT_TENANT_SLUG

DEFAULT_ENTERPRISE_DEPLOY_TARGETS: tuple[str, ...] = (
    "aws-ecs",
    "aws-static-site",
    "github-actions",
)


@dataclass(frozen=True)
class FleetDeployPolicy:
    tenant_slug: str
    allowed_deploy_targets: tuple[str, ...] = DEFAULT_ENTERPRISE_DEPLOY_TARGETS

    def to_dict(self) -> dict[str, Any]:
        return {
            "tenant_slug": self.tenant_slug,
            "allowed_deploy_targets": list(self.allowed_deploy_targets),
        }


def _policies_path(repo_root: Path | None = None) -> Path:
    root = repo_root or find_repo_root()
    return root / "configs" / "enterprise" / "fleet_deploy_policies.yaml"


def _normalize_targets(raw: Any) -> tuple[str, ...]:
    if not isinstance(raw, list):
        return DEFAULT_ENTERPRISE_DEPLOY_TARGETS
    out = tuple(str(item).strip() for item in raw if str(item).strip())
    return out or DEFAULT_ENTERPRISE_DEPLOY_TARGETS


def load_fleet_deploy_policies(
    repo_root: Path | None = None,
) -> dict[str, FleetDeployPolicy]:
    path = _policies_path(repo_root)
    if not path.is_file():
        return {}
    raw = mapping_or_empty(yaml.safe_load(path.read_text(encoding="utf-8")))
    tenants = mapping_or_empty(raw.get("tenants"))
    out: dict[str, FleetDeployPolicy] = {}
    for slug, entry in tenants.items():
        if not isinstance(entry, dict):
            continue
        slug_s = str(slug).strip()
        if not slug_s:
            continue
        out[slug_s] = FleetDeployPolicy(
            tenant_slug=slug_s,
            allowed_deploy_targets=_normalize_targets(entry.get("allowed_deploy_targets")),
        )
    return out


def save_fleet_deploy_policies(
    policies: dict[str, FleetDeployPolicy],
    *,
    repo_root: Path | None = None,
) -> None:
    path = _policies_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    tenants = {
        slug: {"allowed_deploy_targets": list(p.allowed_deploy_targets)}
        for slug, p in sorted(policies.items(), key=lambda x: x[0])
    }
    payload = {"version": 1, "tenants": tenants}
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def tenant_deploy_policy(
    tenant_slug: str | None,
    *,
    repo_root: Path | None = None,
) -> FleetDeployPolicy:
    slug = (tenant_slug or DEFAULT_TENANT_SLUG).strip() or DEFAULT_TENANT_SLUG
    policies = load_fleet_deploy_policies(repo_root)
    if slug in policies:
        return policies[slug]
    if DEFAULT_TENANT_SLUG in policies:
        return policies[DEFAULT_TENANT_SLUG]
    return FleetDeployPolicy(tenant_slug=slug)

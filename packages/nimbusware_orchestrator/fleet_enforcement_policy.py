from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from agent_core.mapping import mapping_or_empty
from nimbusware_env import find_repo_root
from nimbusware_iam.constants import DEFAULT_TENANT_SLUG
from nimbusware_orchestrator.enforcement_profiles import (
    EnforcementProfile,
    resolve_enforcement_profile,
)


@dataclass(frozen=True)
class FleetEnforcementPolicy:
    tenant_slug: str
    min_enforcement_level: int = 0
    max_enforcement_level: int = 10
    required_enforcement_profile_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "tenant_slug": self.tenant_slug,
            "min_enforcement_level": self.min_enforcement_level,
            "max_enforcement_level": self.max_enforcement_level,
            "required_enforcement_profile_id": self.required_enforcement_profile_id,
        }


def _policies_path(repo_root: Path | None = None) -> Path:
    root = repo_root or find_repo_root()
    return root / "configs" / "enterprise" / "fleet_enforcement_policies.yaml"


def load_fleet_enforcement_policies(
    repo_root: Path | None = None,
) -> dict[str, FleetEnforcementPolicy]:
    path = _policies_path(repo_root)
    if not path.is_file():
        return {}
    raw = mapping_or_empty(yaml.safe_load(path.read_text(encoding="utf-8")))
    tenants = mapping_or_empty(raw.get("tenants"))
    out: dict[str, FleetEnforcementPolicy] = {}
    for slug, entry in tenants.items():
        if not isinstance(entry, dict):
            continue
        slug_s = str(slug).strip()
        if not slug_s:
            continue
        out[slug_s] = FleetEnforcementPolicy(
            tenant_slug=slug_s,
            min_enforcement_level=max(0, min(10, int(entry.get("min_enforcement_level") or 0))),
            max_enforcement_level=max(0, min(10, int(entry.get("max_enforcement_level") or 10))),
            required_enforcement_profile_id=str(
                entry.get("required_enforcement_profile_id") or "",
            ).strip(),
        )
    return out


def save_fleet_enforcement_policies(
    policies: dict[str, FleetEnforcementPolicy],
    *,
    repo_root: Path | None = None,
) -> None:
    path = _policies_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    tenants = {
        slug: {
            "min_enforcement_level": p.min_enforcement_level,
            "max_enforcement_level": p.max_enforcement_level,
            "required_enforcement_profile_id": p.required_enforcement_profile_id,
        }
        for slug, p in sorted(policies.items(), key=lambda x: x[0])
    }
    payload = {"version": 1, "tenants": tenants}
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def tenant_enforcement_policy(
    tenant_slug: str | None,
    *,
    repo_root: Path | None = None,
) -> FleetEnforcementPolicy:
    slug = (tenant_slug or DEFAULT_TENANT_SLUG).strip() or DEFAULT_TENANT_SLUG
    policies = load_fleet_enforcement_policies(repo_root)
    if slug in policies:
        return policies[slug]
    if DEFAULT_TENANT_SLUG in policies:
        return policies[DEFAULT_TENANT_SLUG]
    return FleetEnforcementPolicy(tenant_slug=slug)


def clamp_profile_to_policy(
    profile: EnforcementProfile,
    policy: FleetEnforcementPolicy,
) -> EnforcementProfile:
    level = max(policy.min_enforcement_level, min(profile.level, policy.max_enforcement_level))
    if level == profile.level:
        return profile
    return resolve_enforcement_profile(level=level)


def enforce_tenant_enforcement_policy(
    profile: EnforcementProfile,
    tenant_slug: str | None,
    *,
    repo_root: Path | None = None,
) -> EnforcementProfile:
    policy = tenant_enforcement_policy(tenant_slug, repo_root=repo_root)
    required_id = policy.required_enforcement_profile_id.strip()
    if required_id:
        from nimbusware_orchestrator.user_enforcement_profiles import (
            resolve_user_enforcement_profile,
        )

        required = resolve_user_enforcement_profile(required_id, repo_root=repo_root)
        if required is not None:
            profile = required
    return clamp_profile_to_policy(profile, policy)

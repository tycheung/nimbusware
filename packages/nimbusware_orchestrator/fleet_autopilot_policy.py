from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from agent_core.mapping import mapping_or_empty
from nimbusware_env import find_repo_root
from nimbusware_iam.constants import DEFAULT_TENANT_SLUG
from nimbusware_orchestrator.autopilot_profiles import (
    CHECKPOINT_CATALOG,
    AutopilotProfile,
    resolve_autopilot_profile,
)


@dataclass(frozen=True)
class FleetAutopilotPolicy:
    tenant_slug: str
    max_autopilot_level: int = 10
    required_checkpoints: frozenset[str] = frozenset()

    def to_dict(self) -> dict[str, Any]:
        return {
            "tenant_slug": self.tenant_slug,
            "max_autopilot_level": self.max_autopilot_level,
            "required_checkpoints": sorted(self.required_checkpoints),
        }


def _policies_path(repo_root: Path | None = None) -> Path:
    root = repo_root or find_repo_root()
    return root / "configs" / "enterprise" / "fleet_autopilot_policies.yaml"


def load_fleet_autopilot_policies(repo_root: Path | None = None) -> dict[str, FleetAutopilotPolicy]:
    path = _policies_path(repo_root)
    if not path.is_file():
        return {}
    raw = mapping_or_empty(yaml.safe_load(path.read_text(encoding="utf-8")))
    tenants = mapping_or_empty(raw.get("tenants"))
    out: dict[str, FleetAutopilotPolicy] = {}
    for slug, entry in tenants.items():
        if not isinstance(entry, dict):
            continue
        slug_s = str(slug).strip()
        if not slug_s:
            continue
        cps_raw = entry.get("required_checkpoints")
        checkpoints = (
            frozenset(str(c) for c in cps_raw if str(c) in CHECKPOINT_CATALOG)
            if isinstance(cps_raw, list)
            else frozenset()
        )
        out[slug_s] = FleetAutopilotPolicy(
            tenant_slug=slug_s,
            max_autopilot_level=max(0, min(10, int(entry.get("max_autopilot_level") or 10))),
            required_checkpoints=checkpoints,
        )
    return out


def save_fleet_autopilot_policies(
    policies: dict[str, FleetAutopilotPolicy],
    *,
    repo_root: Path | None = None,
) -> None:
    path = _policies_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    tenants = {
        slug: {
            "max_autopilot_level": p.max_autopilot_level,
            "required_checkpoints": sorted(p.required_checkpoints),
        }
        for slug, p in sorted(policies.items(), key=lambda x: x[0])
    }
    payload = {"version": 1, "tenants": tenants}
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def tenant_autopilot_policy(
    tenant_slug: str | None,
    *,
    repo_root: Path | None = None,
) -> FleetAutopilotPolicy:
    slug = (tenant_slug or DEFAULT_TENANT_SLUG).strip() or DEFAULT_TENANT_SLUG
    policies = load_fleet_autopilot_policies(repo_root)
    if slug in policies:
        return policies[slug]
    if DEFAULT_TENANT_SLUG in policies:
        return policies[DEFAULT_TENANT_SLUG]
    return FleetAutopilotPolicy(tenant_slug=slug)


def clamp_profile_to_policy(
    profile: AutopilotProfile,
    policy: FleetAutopilotPolicy,
) -> AutopilotProfile:
    level = min(profile.level, policy.max_autopilot_level)
    checkpoints = set(profile.checkpoints) | set(policy.required_checkpoints)
    valid = {c for c in checkpoints if c in CHECKPOINT_CATALOG}
    if level == profile.level and valid == profile.checkpoints:
        return profile
    return resolve_autopilot_profile(
        level=level,
        custom_checkpoints=valid,
    )


def enforce_tenant_autopilot_policy(
    profile: AutopilotProfile,
    tenant_slug: str | None,
    *,
    repo_root: Path | None = None,
) -> AutopilotProfile:
    policy = tenant_autopilot_policy(tenant_slug, repo_root=repo_root)
    return clamp_profile_to_policy(profile, policy)

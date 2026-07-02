from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from nimbusware_orchestrator.autopilot_profiles import (
    CHECKPOINT_CATALOG,
    AutopilotProfile,
    resolve_autopilot_profile,
)
from nimbusware_orchestrator.fleet_policy_loader import (
    load_tenant_policies,
    save_tenant_policies,
    tenant_policy,
)

_YAML = "fleet_autopilot_policies.yaml"


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


def _parse_entry(slug: str, entry: dict[str, Any]) -> FleetAutopilotPolicy:
    cps_raw = entry.get("required_checkpoints")
    checkpoints = (
        frozenset(str(c) for c in cps_raw if str(c) in CHECKPOINT_CATALOG)
        if isinstance(cps_raw, list)
        else frozenset()
    )
    return FleetAutopilotPolicy(
        tenant_slug=slug,
        max_autopilot_level=max(0, min(10, int(entry.get("max_autopilot_level") or 10))),
        required_checkpoints=checkpoints,
    )


def _serialize_entry(policy: FleetAutopilotPolicy) -> dict[str, Any]:
    return {
        "max_autopilot_level": policy.max_autopilot_level,
        "required_checkpoints": sorted(policy.required_checkpoints),
    }


def load_fleet_autopilot_policies(repo_root: Path | None = None) -> dict[str, FleetAutopilotPolicy]:
    return load_tenant_policies(_YAML, _parse_entry, repo_root=repo_root)


def save_fleet_autopilot_policies(
    policies: dict[str, FleetAutopilotPolicy],
    *,
    repo_root: Path | None = None,
) -> None:
    save_tenant_policies(_YAML, policies, _serialize_entry, repo_root=repo_root)


def tenant_autopilot_policy(
    tenant_slug: str | None,
    *,
    repo_root: Path | None = None,
) -> FleetAutopilotPolicy:
    return tenant_policy(
        tenant_slug,
        load_fleet_autopilot_policies,
        FleetAutopilotPolicy,
        repo_root=repo_root,
    )


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

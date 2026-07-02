from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from nimbusware_orchestrator.autopilot_profiles import (
    CHECKPOINT_CATALOG,
    AutopilotProfile,
    resolve_autopilot_profile,
)
from nimbusware_orchestrator.enforcement_profiles import (
    EnforcementProfile,
    resolve_enforcement_profile,
)
from nimbusware_orchestrator.fleet_policies import (
    FleetAutopilotPolicy,
    FleetEnforcementPolicy,
    tenant_autopilot_policy,
    tenant_enforcement_policy,
    tenant_stack_policy,
)


def clamp_autopilot_profile_to_policy(
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
    return clamp_autopilot_profile_to_policy(profile, policy)


def clamp_enforcement_profile_to_policy(
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
    return clamp_enforcement_profile_to_policy(profile, policy)


def apply_regulated_stack_guard(
    manifest: dict[str, object],
    tenant_slug: str | None,
    *,
    repo_root: Path | None = None,
) -> dict[str, object]:
    policy = tenant_stack_policy(tenant_slug, repo_root=repo_root)
    if not policy.restricts_stacks():
        return manifest
    allowed = policy.allowed_stacks
    out = deepcopy(manifest)
    surfaces_raw = out.get("surfaces")
    surfaces = (
        [str(s).strip().lower() for s in surfaces_raw if str(s).strip()]
        if isinstance(surfaces_raw, list)
        else []
    )
    permitted_surfaces = [s for s in surfaces if s in allowed]
    if not permitted_surfaces:
        permitted_surfaces = sorted(allowed.keys())
    stacks = dict(out.get("stacks") or {}) if isinstance(out.get("stacks"), dict) else {}
    clamps: list[str] = []
    guarded_stacks: dict[str, str] = {}
    for surface in permitted_surfaces:
        permitted_stack = allowed.get(surface)
        if not permitted_stack:
            continue
        prior = stacks.get(surface)
        if prior and prior != permitted_stack:
            clamps.append(f"{surface}:{prior}->{permitted_stack}")
        guarded_stacks[surface] = permitted_stack
    out["surfaces"] = permitted_surfaces
    out["stacks"] = guarded_stacks
    if clamps:
        out["regulated_stack_guard"] = {
            "tenant_slug": policy.tenant_slug,
            "clamps": clamps,
        }
    return out

from __future__ import annotations

from copy import deepcopy
from typing import Any

from nimbusware_maker.archetype_workflow import campaign_profile_for_archetype

_DEFAULT_MANIFEST: dict[str, Any] = {
    "surfaces": ["api", "web"],
    "stacks": {"api": "fastapi_python", "web": "react_vite"},
    "hosting": "local",
    "recommended": True,
}


def default_surfaces_for_archetype(
    *,
    setup_bundle: str = "default",
    archetype: str | None = None,
) -> list[str]:
    _ = archetype
    bundle = (setup_bundle or "default").strip().lower()
    if bundle == "enterprise":
        return ["api", "web"]
    return ["api", "web"]


def apply_fleet_surface_policy(
    manifest: dict[str, Any],
    fleet_policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    out = deepcopy(manifest)
    policy = fleet_policy if isinstance(fleet_policy, dict) else {}
    surfaces = list(out.get("surfaces") or [])
    if policy.get("require_web_surface", True) and "web" not in surfaces:
        surfaces.append("web")
    blocked = policy.get("blocked_surfaces")
    if isinstance(blocked, list):
        surfaces = [s for s in surfaces if s not in blocked]
    if not surfaces:
        surfaces = default_surfaces_for_archetype(setup_bundle="enterprise")
    out["surfaces"] = surfaces
    stacks = dict(out.get("stacks") or {})
    if "web" in surfaces and "web" not in stacks:
        stacks["web"] = "react_vite"
    if "api" in surfaces and "api" not in stacks:
        stacks["api"] = "fastapi_python"
    out["stacks"] = stacks
    return out


def manifest_for_archetype(
    *,
    setup_bundle: str = "default",
    archetype: str | None = None,
    fleet_policy: dict[str, Any] | None = None,
    tenant_slug: str | None = None,
) -> dict[str, Any]:
    manifest = deepcopy(_DEFAULT_MANIFEST)
    manifest["surfaces"] = default_surfaces_for_archetype(
        setup_bundle=setup_bundle,
        archetype=archetype,
    )
    manifest = apply_fleet_surface_policy(manifest, fleet_policy)
    return _apply_regulated_stack_guard(manifest, tenant_slug)


def _apply_regulated_stack_guard(
    manifest: dict[str, Any],
    tenant_slug: str | None,
) -> dict[str, Any]:
    from nimbusware_orchestrator.fleet_policy_guards import apply_regulated_stack_guard


    return apply_regulated_stack_guard(manifest, tenant_slug)


__all__ = [
    "apply_fleet_surface_policy",
    "campaign_profile_for_archetype",
    "default_surfaces_for_archetype",
    "manifest_for_archetype",
]

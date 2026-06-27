from __future__ import annotations

from copy import deepcopy
from typing import Any

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
) -> dict[str, Any]:
    manifest = deepcopy(_DEFAULT_MANIFEST)
    manifest["surfaces"] = default_surfaces_for_archetype(
        setup_bundle=setup_bundle,
        archetype=archetype,
    )
    return apply_fleet_surface_policy(manifest, fleet_policy)


def campaign_profile_for_archetype(
    *,
    setup_bundle: str = "default",
    archetype: str | None = None,
    scope_narrowed: bool = False,
) -> str:
    if scope_narrowed:
        return "campaign_micro_slice"
    arch = (archetype or "").strip().lower().replace("-", "_")
    if arch in {"safe_coding", "a1"}:
        return "campaign_fullstack"
    if (setup_bundle or "").strip().lower() == "enterprise":
        return "campaign_fullstack"
    return "campaign_fullstack"

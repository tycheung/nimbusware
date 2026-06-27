from __future__ import annotations

from typing import Any

from nimbusware_env.env_flags import env_str
from nimbusware_maker.archetype_surface_defaults import default_surfaces_for_archetype


def fleet_governance_summary(
    *,
    setup_bundle: str | None = None,
    archetype: str | None = None,
    tenant_slug: str | None = None,
) -> dict[str, Any]:
    from nimbusware_orchestrator.fleet_enforcement_policy import tenant_enforcement_policy

    bundle = (setup_bundle or env_str("NIMBUSWARE_SETUP_BUNDLE").strip() or "default").lower()
    enforcement = tenant_enforcement_policy(tenant_slug or None)
    surfaces = default_surfaces_for_archetype(setup_bundle=bundle, archetype=archetype)
    mandatory_discovery = bundle == "enterprise"
    return {
        "setup_bundle": bundle,
        "mandatory_discovery": mandatory_discovery,
        "default_surfaces": surfaces,
        "surface_policy": {
            "require_web_surface": bundle == "enterprise",
            "blocked_surfaces": [],
        },
        "enforcement_policy": enforcement.to_dict(),
        "deploy_chain_required": bundle == "enterprise",
    }

from __future__ import annotations

from typing import Any

from nimbusware_env.env_flags import env_str
from nimbusware_maker.archetype_surface_defaults import default_surfaces_for_archetype
from nimbusware_maker.deploy_target_enforcement import allowed_deploy_targets_for_tenant


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
        "allowed_deploy_targets": allowed_deploy_targets_for_tenant(
            tenant_slug,
            setup_bundle=bundle,
        ),
        "discovery_required_fields": _discovery_required_fields(tenant_slug, bundle),
        "deploy_approval_chain": _deploy_approval_chain(tenant_slug, bundle),
        "allowed_stacks": _allowed_stacks(tenant_slug, bundle),
    }


def _allowed_stacks(tenant_slug: str | None, bundle: str) -> dict[str, str]:
    if bundle != "enterprise":
        return {}
    from nimbusware_orchestrator.fleet_stack_policy import tenant_stack_policy

    policy = tenant_stack_policy(tenant_slug)
    return dict(policy.allowed_stacks)


def _deploy_approval_chain(tenant_slug: str | None, bundle: str) -> str:
    if bundle != "enterprise":
        return "maker_only"
    from nimbusware_orchestrator.fleet_deploy_approval_policy import tenant_deploy_approval_policy

    return tenant_deploy_approval_policy(tenant_slug).deploy_approval_chain


def _discovery_required_fields(tenant_slug: str | None, bundle: str) -> list[str]:
    if bundle != "enterprise":
        return []
    from nimbusware_orchestrator.fleet_discovery_policy import tenant_discovery_policy

    return list(tenant_discovery_policy(tenant_slug).discovery_required_fields)

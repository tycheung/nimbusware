from __future__ import annotations

from env.env_flags import env_str
from orchestrator.fleet_policies import tenant_slice_policy


def clamp_slice_budget(
    max_files: int,
    max_loc: int,
    *,
    tenant_slug: str | None,
    setup_bundle: str | None = None,
) -> tuple[int, int, bool]:
    bundle = (setup_bundle or env_str("NIMBUSWARE_SETUP_BUNDLE").strip() or "default").lower()
    if bundle != "enterprise":
        return max_files, max_loc, False
    policy = tenant_slice_policy(tenant_slug)
    capped_files = min(max_files, policy.max_files)
    capped_loc = min(max_loc, policy.max_loc)
    fleet_active = capped_files < max_files or capped_loc < max_loc
    return capped_files, capped_loc, fleet_active


def fleet_replan_metadata(*, fleet_cap_active: bool) -> dict[str, str]:
    if not fleet_cap_active:
        return {}
    return {
        "fleet_cap_triggered": "true",
        "fleet_cap_cta": "Slice exceeded tenant fleet cap — replanning with narrower target paths",
    }

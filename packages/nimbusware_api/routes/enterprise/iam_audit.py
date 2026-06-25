from __future__ import annotations

from typing import Any

from nimbusware_iam.context import get_auth_context


def log_fleet_policy_updated(
    iam: Any,
    *,
    tenant_slug: str,
    policy_kind: str,
) -> None:
    if not hasattr(iam, "log_iam_action"):
        return
    ctx = get_auth_context()
    iam.log_iam_action(
        action="iam.policy.updated",
        tenant_id=ctx.tenant_id if ctx else None,
        actor_key_id=ctx.key_id if ctx else None,
        detail={"tenant_slug": tenant_slug, "policy_kind": policy_kind},
    )

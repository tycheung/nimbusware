from __future__ import annotations

from collections.abc import Callable
from typing import Any

from api.deps import IamStoreDep
from api.routes.enterprise.fleet_enforcement import _tenant_slug_for_ref
from api.routes.enterprise.iam_audit import log_fleet_policy_updated


def fleet_tenant_policy_get(
    iam: IamStoreDep,
    tenant_ref: str,
    resolver: Callable[[str], Any],
) -> dict[str, Any]:
    slug = _tenant_slug_for_ref(iam, tenant_ref)
    return resolver(slug).to_dict()


def fleet_tenant_policy_put(
    iam: IamStoreDep,
    tenant_ref: str,
    *,
    policy_kind: str,
    policy: Any,
    load_policies: Callable[[], dict[str, Any]],
    save_policies: Callable[[dict[str, Any]], None],
) -> dict[str, Any]:
    slug = _tenant_slug_for_ref(iam, tenant_ref)
    policies = load_policies()
    policies[slug] = policy
    save_policies(policies)
    log_fleet_policy_updated(iam, tenant_slug=slug, policy_kind=policy_kind)
    return policies[slug].to_dict()

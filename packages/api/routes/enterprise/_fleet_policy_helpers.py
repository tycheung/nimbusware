from __future__ import annotations

from collections.abc import Callable
from typing import Any
from uuid import UUID

from fastapi import HTTPException

from api.deps import IamStoreDep
from api.errors import problem
from api.routes.enterprise.iam_audit import log_fleet_policy_updated


def tenant_slug_for_ref(iam: IamStoreDep, tenant_ref: str) -> str:
    ref = tenant_ref.strip()
    if not ref:
        raise HTTPException(
            status_code=422,
            detail=problem("invalid_tenant", "tenant reference required"),
        )
    try:
        tid = UUID(ref)
        tenant = iam.get_tenant(tid)
        if tenant is None:
            raise HTTPException(
                status_code=404,
                detail=problem("tenant_not_found", f"unknown tenant_id: {ref}"),
            )
        return tenant.slug
    except ValueError:
        for tenant in iam.list_tenants():
            if tenant.slug == ref:
                return tenant.slug
        return ref


def fleet_tenant_policy_get(
    iam: IamStoreDep,
    tenant_ref: str,
    resolver: Callable[[str], Any],
) -> dict[str, Any]:
    slug = tenant_slug_for_ref(iam, tenant_ref)
    resolved = resolver(slug)
    return dict(resolved.to_dict())


def fleet_tenant_policy_put(
    iam: IamStoreDep,
    tenant_ref: str,
    *,
    policy_kind: str,
    policy: Any,
    load_policies: Callable[[], dict[str, Any]],
    save_policies: Callable[[dict[str, Any]], None],
) -> dict[str, Any]:
    slug = tenant_slug_for_ref(iam, tenant_ref)
    policies = load_policies()
    policies[slug] = policy
    save_policies(policies)
    log_fleet_policy_updated(iam, tenant_slug=slug, policy_kind=policy_kind)
    return dict(policies[slug].to_dict())

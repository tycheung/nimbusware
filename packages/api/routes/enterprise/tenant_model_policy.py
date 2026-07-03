from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from api.deps import IamStoreDep
from api.routes.enterprise.core import EnterpriseDep
from api.routes.enterprise.fleet_enforcement import _tenant_slug_for_ref
from api.routes.enterprise.iam_audit import log_fleet_policy_updated
from config.tenant_policy_store import (
    load_tenant_model_policy,
    save_tenant_model_policy,
)

router = APIRouter(prefix="/enterprise", tags=["enterprise"])


class TenantModelPolicyBody(BaseModel):
    allowed_cloud_providers: list[str] = Field(default_factory=list)
    require_admin_for_cloud_swap: bool = False
    blocked_model_ids: list[str] = Field(default_factory=list)
    audit_include_binding_events: bool = True


@router.get("/tenants/{tenant_ref}/model-policy")
def get_tenant_model_policy(
    tenant_ref: str,
    _: EnterpriseDep,
    iam: IamStoreDep,
) -> dict[str, Any]:
    slug = _tenant_slug_for_ref(iam, tenant_ref)
    policy = load_tenant_model_policy(slug)
    return {"tenant_slug": slug, "version": int(policy.get("version") or 1), **policy}


@router.put("/tenants/{tenant_ref}/model-policy")
def put_tenant_model_policy(
    tenant_ref: str,
    body: TenantModelPolicyBody,
    _: EnterpriseDep,
    iam: IamStoreDep,
) -> dict[str, Any]:
    slug = _tenant_slug_for_ref(iam, tenant_ref)
    doc = {
        "version": 1,
        "allowed_cloud_providers": list(body.allowed_cloud_providers),
        "require_admin_for_cloud_swap": body.require_admin_for_cloud_swap,
        "blocked_model_ids": list(body.blocked_model_ids),
        "audit_include_binding_events": body.audit_include_binding_events,
    }
    saved = save_tenant_model_policy(slug, doc)
    log_fleet_policy_updated(iam, tenant_slug=slug, policy_kind="tenant_model")
    return {"tenant_slug": slug, "ok": True, "policy": saved}

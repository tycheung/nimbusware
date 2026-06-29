from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from nimbusware_api.deps import IamStoreDep
from nimbusware_api.routes.enterprise.core import EnterpriseDep
from nimbusware_api.routes.enterprise.fleet_enforcement import _tenant_slug_for_ref
from nimbusware_api.routes.enterprise.iam_audit import log_fleet_policy_updated
from nimbusware_config.tenant_policy_store import (
    load_tenant_collab_policy,
    save_tenant_collab_policy,
)

router = APIRouter(prefix="/enterprise", tags=["enterprise"])


class TenantCollabPolicyBody(BaseModel):
    allow_external_collaborators: bool = False
    max_session_participants: int = Field(default=20, ge=1, le=500)
    host_transfer_consent_hours: int = Field(default=24, ge=1, le=168)
    default_invite_role: str = Field(default="session_read", max_length=32)
    write_may_start_runs: bool = False
    default_join_discipline: str | None = Field(default=None, max_length=32)
    default_agent_overlays: dict[str, str] = Field(default_factory=dict)


@router.get("/tenants/{tenant_ref}/collab-policy")
def get_tenant_collab_policy(
    tenant_ref: str,
    _: EnterpriseDep,
    iam: IamStoreDep,
) -> dict[str, Any]:
    slug = _tenant_slug_for_ref(iam, tenant_ref)
    policy = load_tenant_collab_policy(slug)
    return {"tenant_slug": slug, "version": int(policy.get("version") or 1), **policy}


@router.put("/tenants/{tenant_ref}/collab-policy")
def put_tenant_collab_policy(
    tenant_ref: str,
    body: TenantCollabPolicyBody,
    _: EnterpriseDep,
    iam: IamStoreDep,
) -> dict[str, Any]:
    slug = _tenant_slug_for_ref(iam, tenant_ref)
    doc = {
        "version": 1,
        "allow_external_collaborators": body.allow_external_collaborators,
        "max_session_participants": body.max_session_participants,
        "host_transfer_consent_hours": body.host_transfer_consent_hours,
        "default_invite_role": body.default_invite_role,
        "write_may_start_runs": body.write_may_start_runs,
        "default_join_discipline": body.default_join_discipline,
        "default_agent_overlays": {
            str(k): str(v)[:2000]
            for k, v in (body.default_agent_overlays or {}).items()
            if str(k).strip()
        },
    }
    saved = save_tenant_collab_policy(slug, doc)
    log_fleet_policy_updated(iam, tenant_slug=slug, policy_kind="tenant_collab")
    return {"tenant_slug": slug, "ok": True, "policy": saved}

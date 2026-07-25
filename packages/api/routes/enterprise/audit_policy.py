from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from api.routes.enterprise.core import EnterpriseDep
from api.schemas.peel_responses import with_enterprise_peel_503
from config.tenant_policy_store import load_tenant_audit_policy, save_tenant_audit_policy

router = APIRouter(prefix="/enterprise", tags=["enterprise"])


class AuditPolicyBody(BaseModel):
    legal_hold: bool = False
    redaction_patterns: list[str] = Field(default_factory=list)


class AuditPolicyResponse(BaseModel):
    """GET/PUT /enterprise/audit-policy (`sak481-c`)."""

    model_config = {"extra": "allow"}

    version: int | None = None
    legal_hold: bool = False
    redaction_patterns: list[str] = Field(default_factory=list)
    via: str | None = None
    error: str | None = None
    feature: str | None = None


@router.get(
    "/audit-policy",
    response_model=AuditPolicyResponse,
    response_model_exclude_none=True,
    summary="Tenant audit policy (`sak481-c`)",
    responses=with_enterprise_peel_503(),  # sak519-c
)
def get_audit_policy(_: EnterpriseDep, tenant_slug: str = "default") -> dict[str, Any]:
    return load_tenant_audit_policy(tenant_slug)


@router.put(
    "/audit-policy",
    response_model=AuditPolicyResponse,
    response_model_exclude_none=True,
    summary="Update tenant audit policy (`sak481-c`)",
    responses=with_enterprise_peel_503(),  # sak519-c
)
def put_audit_policy(
    body: AuditPolicyBody,
    _: EnterpriseDep,
    tenant_slug: str = "default",
) -> dict[str, Any]:
    doc = {
        "version": 1,
        "legal_hold": body.legal_hold,
        "redaction_patterns": [str(p).strip() for p in body.redaction_patterns if str(p).strip()],
    }
    return save_tenant_audit_policy(tenant_slug, doc)

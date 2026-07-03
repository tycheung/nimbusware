from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from api.routes.enterprise.core import EnterpriseDep
from config.tenant_policy_store import load_tenant_audit_policy, save_tenant_audit_policy

router = APIRouter(prefix="/enterprise", tags=["enterprise"])


class AuditPolicyBody(BaseModel):
    legal_hold: bool = False
    redaction_patterns: list[str] = Field(default_factory=list)


@router.get("/audit-policy")
def get_audit_policy(_: EnterpriseDep, tenant_slug: str = "default") -> dict[str, Any]:
    return load_tenant_audit_policy(tenant_slug)


@router.put("/audit-policy")
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

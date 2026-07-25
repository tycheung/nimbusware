from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from api.admin import AdminDep
from api.deps import IamStoreDep
from api.routes.enterprise._fleet_policy_helpers import (
    fleet_tenant_policy_get,
    fleet_tenant_policy_put,
    tenant_slug_for_ref,
)
from api.routes.enterprise.core import EnterpriseDep
from api.schemas.peel_responses import with_enterprise_peel_503
from orchestrator.fleet.policies import (
    FleetStandardsPolicy,
    load_fleet_standards_policies,
    save_fleet_standards_policies,
    tenant_standards_policy,
)

router = APIRouter(prefix="/enterprise", tags=["enterprise"])


class FleetStandardsPolicyBody(BaseModel):
    min_bundle_ids: list[str] = Field(default_factory=list)
    blocked_origins: list[str] = Field(default_factory=lambda: ["community"])
    required_facade_id: str = Field(default="", max_length=120)


class FleetStandardsPolicyResponse(BaseModel):
    """GET/PUT tenant standards-policy (`sak483-f`)."""

    model_config = {"extra": "allow"}

    tenant_slug: str | None = None
    min_bundle_ids: list[str] | None = None
    blocked_origins: list[str] | None = None
    required_facade_id: str | None = None
    via: str | None = None
    error: str | None = None
    feature: str | None = None


@router.get(
    "/tenants/{tenant_ref}/standards-policy",
    response_model=FleetStandardsPolicyResponse,
    response_model_exclude_none=True,
    summary="Tenant standards policy GET (`sak483-f`)",
    responses=with_enterprise_peel_503(),  # sak503-c / sak503-d
)
def get_tenant_standards_policy(
    tenant_ref: str,
    _gate: EnterpriseDep,
    iam: IamStoreDep,
) -> dict[str, Any]:
    return fleet_tenant_policy_get(iam, tenant_ref, tenant_standards_policy)


@router.put(
    "/tenants/{tenant_ref}/standards-policy",
    response_model=FleetStandardsPolicyResponse,
    response_model_exclude_none=True,
    summary="Tenant standards policy PUT (`sak483-f`)",
    responses=with_enterprise_peel_503(),  # sak518-h
)
def put_tenant_standards_policy(
    tenant_ref: str,
    body: FleetStandardsPolicyBody,
    _admin: AdminDep,
    _gate: EnterpriseDep,
    iam: IamStoreDep,
) -> dict[str, Any]:
    slug = tenant_slug_for_ref(iam, tenant_ref)

    def _save(policies: dict[str, Any]) -> None:
        save_fleet_standards_policies(policies)

    return fleet_tenant_policy_put(
        iam,
        tenant_ref,
        policy_kind="standards",
        policy=FleetStandardsPolicy(
            tenant_slug=slug,
            min_bundle_ids=tuple(b.strip() for b in body.min_bundle_ids if b.strip()),
            blocked_origins=tuple(o.strip() for o in body.blocked_origins if o.strip())
            or ("community",),
            required_facade_id=body.required_facade_id.strip(),
        ),
        load_policies=load_fleet_standards_policies,
        save_policies=_save,
    )

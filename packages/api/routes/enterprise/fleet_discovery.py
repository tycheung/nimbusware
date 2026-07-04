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
from orchestrator.fleet.policies import (
    VALID_DISCOVERY_FIELD_IDS,
    FleetDiscoveryPolicy,
    load_fleet_discovery_policies,
    save_fleet_discovery_policies,
    tenant_discovery_policy,
)

router = APIRouter(prefix="/enterprise", tags=["enterprise"])


class FleetDiscoveryPolicyBody(BaseModel):
    discovery_required_fields: list[str] = Field(default_factory=list, max_length=12)


@router.get("/tenants/{tenant_ref}/discovery-policy")
def get_fleet_discovery_policy(
    tenant_ref: str,
    _: EnterpriseDep,
    iam: IamStoreDep,
    __: AdminDep,
) -> dict[str, Any]:
    return fleet_tenant_policy_get(iam, tenant_ref, tenant_discovery_policy)


@router.put("/tenants/{tenant_ref}/discovery-policy")
def put_fleet_discovery_policy(
    tenant_ref: str,
    body: FleetDiscoveryPolicyBody,
    _: EnterpriseDep,
    iam: IamStoreDep,
    __: AdminDep,
) -> dict[str, Any]:
    slug = tenant_slug_for_ref(iam, tenant_ref)
    fields = tuple(
        str(item).strip()
        for item in body.discovery_required_fields
        if str(item).strip() in VALID_DISCOVERY_FIELD_IDS
    )
    policy = FleetDiscoveryPolicy(
        tenant_slug=slug,
        discovery_required_fields=fields,
    )
    return fleet_tenant_policy_put(
        iam,
        tenant_ref,
        policy_kind="discovery",
        policy=policy,
        load_policies=load_fleet_discovery_policies,
        save_policies=save_fleet_discovery_policies,
    )

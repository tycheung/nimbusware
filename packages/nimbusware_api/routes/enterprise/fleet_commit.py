from __future__ import annotations

import re
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from nimbusware_api.admin import AdminDep
from nimbusware_api.deps import IamStoreDep
from nimbusware_api.routes.enterprise.core import EnterpriseDep
from nimbusware_api.routes.enterprise.fleet_enforcement import _tenant_slug_for_ref
from nimbusware_api.routes.enterprise.iam_audit import log_fleet_policy_updated
from nimbusware_orchestrator.fleet_commit_policy import (
    FleetCommitPolicy,
    load_fleet_commit_policies,
    save_fleet_commit_policies,
    tenant_commit_policy,
)

router = APIRouter(prefix="/enterprise", tags=["enterprise"])


class FleetCommitPolicyBody(BaseModel):
    require_auto_commit: bool = False
    message_regex: str = Field(default="", max_length=256)


@router.get("/tenants/{tenant_ref}/commit-policy")
def get_fleet_commit_policy(
    tenant_ref: str,
    _: EnterpriseDep,
    iam: IamStoreDep,
    __: AdminDep,
) -> dict[str, Any]:
    slug = _tenant_slug_for_ref(iam, tenant_ref)
    return tenant_commit_policy(slug).to_dict()


@router.put("/tenants/{tenant_ref}/commit-policy")
def put_fleet_commit_policy(
    tenant_ref: str,
    body: FleetCommitPolicyBody,
    _: EnterpriseDep,
    iam: IamStoreDep,
    __: AdminDep,
) -> dict[str, Any]:
    slug = _tenant_slug_for_ref(iam, tenant_ref)
    if body.message_regex.strip():
        try:
            re.compile(body.message_regex.strip())
        except re.error as exc:
            from fastapi import HTTPException

            from nimbusware_api.errors import problem

            raise HTTPException(
                status_code=422,
                detail=problem("invalid_request", "message_regex is not valid"),
            ) from exc
    policies = load_fleet_commit_policies()
    policies[slug] = FleetCommitPolicy(
        tenant_slug=slug,
        require_auto_commit=body.require_auto_commit,
        message_regex=body.message_regex.strip(),
    )
    save_fleet_commit_policies(policies)
    log_fleet_policy_updated(iam, tenant_slug=slug, policy_kind="commit")
    return policies[slug].to_dict()

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from api.routes.enterprise.core import EnterpriseDep
from api.schemas.peel_responses import with_enterprise_peel_503
from config.model_policy_store import load_model_policy, save_model_policy
from env.dotenv import find_repo_root

router = APIRouter(tags=["enterprise"])


class ModelPolicyBody(BaseModel):
    allowed_cloud_providers: list[str] = Field(default_factory=list)
    require_admin_for_cloud_swap: bool = False
    blocked_model_ids: list[str] = Field(default_factory=list)
    audit_include_binding_events: bool = True


class ModelPolicyResponse(BaseModel):
    """GET/PUT /model-policy (`sak486-f`)."""

    model_config = {"extra": "allow"}

    version: int | None = None
    allowed_cloud_providers: list[str] | None = None
    require_admin_for_cloud_swap: bool | None = None
    blocked_model_ids: list[str] | None = None
    audit_include_binding_events: bool | None = None
    ok: bool | None = None
    policy: dict[str, Any] | None = None
    via: str | None = None
    error: str | None = None
    feature: str | None = None


@router.get(
    "/model-policy",
    response_model=ModelPolicyResponse,
    response_model_exclude_none=True,
    summary="Global model policy GET (`sak486-f`)",
    responses=with_enterprise_peel_503(),  # sak519-g
)
def get_model_policy(_: EnterpriseDep) -> dict[str, Any]:
    policy = load_model_policy(find_repo_root())
    return {"version": int(policy.get("version") or 1), **policy}


@router.put(
    "/model-policy",
    response_model=ModelPolicyResponse,
    response_model_exclude_none=True,
    summary="Global model policy PUT (`sak486-f`)",
    responses=with_enterprise_peel_503(),  # sak519-g
)
def put_model_policy(body: ModelPolicyBody, _: EnterpriseDep) -> dict[str, Any]:
    repo = find_repo_root()
    doc = {
        "version": 1,
        "allowed_cloud_providers": list(body.allowed_cloud_providers),
        "require_admin_for_cloud_swap": body.require_admin_for_cloud_swap,
        "blocked_model_ids": list(body.blocked_model_ids),
        "audit_include_binding_events": body.audit_include_binding_events,
    }
    save_model_policy(repo, doc)
    return {"ok": True, "policy": doc}

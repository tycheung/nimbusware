from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from api.routes.enterprise.core import EnterpriseDep
from config.model_policy_store import load_model_policy, save_model_policy
from env.dotenv import find_repo_root

router = APIRouter(tags=["enterprise"])


class ModelPolicyBody(BaseModel):
    allowed_cloud_providers: list[str] = Field(default_factory=list)
    require_admin_for_cloud_swap: bool = False
    blocked_model_ids: list[str] = Field(default_factory=list)
    audit_include_binding_events: bool = True


@router.get("/model-policy")
def get_model_policy(_: EnterpriseDep) -> dict[str, Any]:
    policy = load_model_policy(find_repo_root())
    return {"version": int(policy.get("version") or 1), **policy}


@router.put("/model-policy")
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

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from api.routes.enterprise.core import EnterpriseDep
from api.schemas.peel_responses import with_enterprise_peel_503
from config.collab_policy_store import load_collab_policy, save_collab_policy
from env.dotenv import find_repo_root

router = APIRouter(tags=["enterprise"])


class CollabPolicyBody(BaseModel):
    allow_external_collaborators: bool = False
    max_session_participants: int = Field(default=20, ge=1, le=500)
    host_transfer_consent_hours: int = Field(default=24, ge=1, le=168)
    default_invite_role: str = Field(default="session_read", max_length=32)
    write_may_start_runs: bool = False


class CollabPolicyResponse(BaseModel):
    """GET/PUT /collab-policy (`sak486-f`)."""

    model_config = {"extra": "allow"}

    version: int | None = None
    allow_external_collaborators: bool | None = None
    max_session_participants: int | None = None
    host_transfer_consent_hours: int | None = None
    default_invite_role: str | None = None
    write_may_start_runs: bool | None = None
    ok: bool | None = None
    policy: dict[str, Any] | None = None
    via: str | None = None
    error: str | None = None
    feature: str | None = None


@router.get(
    "/collab-policy",
    response_model=CollabPolicyResponse,
    response_model_exclude_none=True,
    summary="Global collab policy GET (`sak486-f`)",
    responses=with_enterprise_peel_503(),  # sak519-h
)
def get_collab_policy(_: EnterpriseDep) -> dict[str, Any]:
    policy = load_collab_policy(find_repo_root())
    return {"version": int(policy.get("version") or 1), **policy}


@router.put(
    "/collab-policy",
    response_model=CollabPolicyResponse,
    response_model_exclude_none=True,
    summary="Global collab policy PUT (`sak486-f`)",
    responses=with_enterprise_peel_503(),  # sak519-h
)
def put_collab_policy(body: CollabPolicyBody, _: EnterpriseDep) -> dict[str, Any]:
    repo = find_repo_root()
    doc = {
        "version": 1,
        "allow_external_collaborators": body.allow_external_collaborators,
        "max_session_participants": body.max_session_participants,
        "host_transfer_consent_hours": body.host_transfer_consent_hours,
        "default_invite_role": body.default_invite_role,
        "write_may_start_runs": body.write_may_start_runs,
    }
    save_collab_policy(repo, doc)
    return {"ok": True, "policy": doc}

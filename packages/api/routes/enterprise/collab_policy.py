from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from api.routes.enterprise.core import EnterpriseDep
from config.collab_policy_store import load_collab_policy, save_collab_policy
from env.dotenv import find_repo_root

router = APIRouter(tags=["enterprise"])


class CollabPolicyBody(BaseModel):
    allow_external_collaborators: bool = False
    max_session_participants: int = Field(default=20, ge=1, le=500)
    host_transfer_consent_hours: int = Field(default=24, ge=1, le=168)
    default_invite_role: str = Field(default="session_read", max_length=32)
    write_may_start_runs: bool = False


@router.get("/collab-policy")
def get_collab_policy(_: EnterpriseDep) -> dict[str, Any]:
    policy = load_collab_policy(find_repo_root())
    return {"version": int(policy.get("version") or 1), **policy}


@router.put("/collab-policy")
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

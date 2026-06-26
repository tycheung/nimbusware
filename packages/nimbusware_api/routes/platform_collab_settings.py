from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from nimbusware_api.errors import problem
from nimbusware_api.routes.auth import AuthUserDep
from nimbusware_api.user import maker_user_id_str
from nimbusware_config.collab_settings_store import save_persisted_collab_enabled
from nimbusware_env import find_repo_root
from nimbusware_env.collab_runtime import collab_settings_snapshot, set_runtime_collab_enabled
from nimbusware_env.edition import edition_manifest

router = APIRouter(tags=["platform"])


class CollabSettingsBody(BaseModel):
    collab_enabled: bool


def _require_individual_owner(request: Request, user: AuthUserDep) -> str:
    uid = str(user.user_id) if user is not None else maker_user_id_str(request)
    if not uid:
        raise HTTPException(
            status_code=401,
            detail=problem("unauthorized", "user identity required"),
        )
    edition = edition_manifest()
    if str(edition.get("edition") or "").lower() == "enterprise":
        raise HTTPException(
            status_code=403,
            detail=problem("forbidden", "collab settings are managed via enterprise policy"),
        )
    return uid


@router.get("/platform/collab-settings")
def get_collab_settings(request: Request, user: AuthUserDep) -> dict[str, Any]:
    _require_individual_owner(request, user)
    return collab_settings_snapshot()


@router.put("/platform/collab-settings")
def put_collab_settings(
    body: CollabSettingsBody,
    request: Request,
    user: AuthUserDep,
) -> dict[str, Any]:
    _require_individual_owner(request, user)
    set_runtime_collab_enabled(body.collab_enabled)
    save_persisted_collab_enabled(body.collab_enabled, repo_root=find_repo_root())
    return collab_settings_snapshot()

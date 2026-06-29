from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from nimbusware_api.deps import OrchDep
from nimbusware_maker.collab_disciplines import list_disciplines
from nimbusware_maker.collab_invite_templates import list_invite_templates

router = APIRouter(tags=["platform"])


@router.get("/platform/collab-disciplines")
def get_collab_disciplines(orch: OrchDep) -> dict[str, Any]:
    return {"disciplines": list_disciplines(repo_root=orch.repo_root)}


@router.get("/platform/invite-templates")
def get_invite_templates(orch: OrchDep) -> dict[str, Any]:
    return {"templates": list_invite_templates(repo_root=orch.repo_root)}

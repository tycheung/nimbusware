from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from nimbusware_api.deps import OrchDep
from nimbusware_maker.collab_disciplines import list_disciplines

router = APIRouter(tags=["platform"])


@router.get("/platform/collab-disciplines")
def get_collab_disciplines(orch: OrchDep) -> dict[str, Any]:
    return {"disciplines": list_disciplines(repo_root=orch.repo_root)}

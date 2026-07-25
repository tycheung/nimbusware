from __future__ import annotations

from copy import deepcopy
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel

from api.admin import AdminDep
from api.deps import OrchDep
from api.errors import problem
from api.schemas.peel_responses import long_tail_json_openapi_responses, with_long_tail_peel_503
from config.keys import NS_CRITIC_PACKS
from orchestrator.critique.pack_resolve import (
    list_critic_pack_ids,
    list_workflows_using_critic_pack,
    load_critic_pack,
)

router = APIRouter(prefix="/config/critic-packs", tags=["config"])


class CriticPackListResponse(BaseModel):
    """GET /config/critic-packs (`sak487-f`)."""

    model_config = {"extra": "allow"}

    pack_ids: list[str] | None = None
    count: int | None = None
    via: str | None = None
    error: str | None = None
    feature: str | None = None


class CriticPackWorkflowsResponse(BaseModel):
    """GET /config/critic-packs/{pack_id}/workflows (`sak487-f`)."""

    model_config = {"extra": "allow"}

    pack_id: str | None = None
    workflow_profiles: list[str] | None = None
    count: int | None = None
    via: str | None = None
    error: str | None = None
    feature: str | None = None


class CriticPackDetailResponse(BaseModel):
    """GET /config/critic-packs/{pack_id} (`sak487-f`)."""

    model_config = {"extra": "allow"}

    pack_id: str | None = None
    content: dict[str, Any] | None = None
    via: str | None = None
    error: str | None = None
    feature: str | None = None


class CriticPackUpsertResponse(BaseModel):
    """PUT /config/critic-packs/{pack_id} (`sak487-f`)."""

    model_config = {"extra": "allow"}

    pack_id: str | None = None
    namespace: str | None = None
    version: int | None = None
    via: str | None = None
    error: str | None = None
    feature: str | None = None


def _materializer(orch: Any) -> Any | None:
    return getattr(orch, "config_materializer", None)


@router.get(
    "",
    response_model=CriticPackListResponse,
    response_model_exclude_none=True,
    responses=long_tail_json_openapi_responses(),  # sak503-a
)
def list_critic_packs(_admin: AdminDep, orch: OrchDep) -> dict[str, Any]:
    ids = list_critic_pack_ids(orch.repo_root, config_materializer=_materializer(orch))
    return {"pack_ids": ids, "count": len(ids)}


@router.get(
    "/{pack_id}/workflows",
    response_model=CriticPackWorkflowsResponse,
    response_model_exclude_none=True,
    responses=with_long_tail_peel_503(),  # sak505-c
)
def critic_pack_workflows(
    _admin: AdminDep,
    orch: OrchDep,
    pack_id: Annotated[str, Path(min_length=1, max_length=128)],
) -> dict[str, Any]:
    pack = load_critic_pack(orch.repo_root, pack_id, config_materializer=_materializer(orch))
    if pack is None:
        raise HTTPException(
            status_code=404,
            detail=problem("critic_pack_not_found", f"unknown critic pack: {pack_id}"),
        )
    profiles = list_workflows_using_critic_pack(orch.repo_root, pack_id)
    return {"pack_id": pack_id, "workflow_profiles": profiles, "count": len(profiles)}


@router.get(
    "/{pack_id}",
    response_model=CriticPackDetailResponse,
    response_model_exclude_none=True,
    responses=with_long_tail_peel_503(),  # sak505-c
)
def get_critic_pack(
    _admin: AdminDep,
    orch: OrchDep,
    pack_id: Annotated[str, Path(min_length=1, max_length=128)],
) -> dict[str, Any]:
    pack = load_critic_pack(orch.repo_root, pack_id, config_materializer=_materializer(orch))
    if pack is None:
        raise HTTPException(
            status_code=404,
            detail=problem("critic_pack_not_found", f"unknown critic pack: {pack_id}"),
        )
    return {"pack_id": pack_id, "content": pack}


@router.put(
    "/{pack_id}",
    response_model=CriticPackUpsertResponse,
    response_model_exclude_none=True,
    responses=with_long_tail_peel_503(),  # sak512-b
)
def put_critic_pack(
    _admin: AdminDep,
    orch: OrchDep,
    pack_id: Annotated[str, Path(min_length=1, max_length=128)],
    body: dict[str, Any],
) -> dict[str, Any]:
    mat = _materializer(orch)
    if mat is None or not getattr(mat, "use_db", False):
        raise HTTPException(
            status_code=503,
            detail=problem(
                "critic_packs_postgres_required",
                "critic pack writes require Postgres config store",
            ),
        )
    content = deepcopy(body)
    content.setdefault("id", pack_id)
    version = mat.upsert_critic_pack(pack_id, content)
    return {"pack_id": pack_id, "namespace": NS_CRITIC_PACKS, "version": version}

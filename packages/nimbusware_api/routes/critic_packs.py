from __future__ import annotations

from copy import deepcopy
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Path

from hermes_orchestrator.critic_pack_resolve import list_critic_pack_ids, load_critic_pack
from nimbusware_api.admin import AdminDep
from nimbusware_api.deps import OrchDep
from nimbusware_api.errors import problem
from nimbusware_config.keys import NS_CRITIC_PACKS

router = APIRouter(prefix="/config/critic-packs", tags=["config"])


def _materializer(orch: Any) -> Any | None:
    return getattr(orch, "config_materializer", None)


@router.get("")
def list_critic_packs(_admin: AdminDep, orch: OrchDep) -> dict[str, Any]:
    ids = list_critic_pack_ids(orch.repo_root, config_materializer=_materializer(orch))
    return {"pack_ids": ids, "count": len(ids)}


@router.get("/{pack_id}")
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


@router.put("/{pack_id}")
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

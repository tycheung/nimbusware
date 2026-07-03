from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from api.deps import StoreDep
from api.errors import problem
from api.routes.enterprise.core import EnterpriseDep
from env.edition import enterprise_feature_enabled
from env.env_flags import nimbusware_database_url
from iam.context import get_auth_context
from memory.factory import build_memory_chunk_store
from memory.fleet.index import rebuild_fleet_memory_index
from memory.fleet.sync import (
    fleet_memory_remote_status,
    pull_fleet_memory_from_canonical,
    push_fleet_memory_to_canonical,
)
from memory.index.embeddings import resolve_fleet_embedding_mode
from memory.index.search import format_memory_excerpt, search_fleet_memory
from memory.org_scope import fleet_scope_hash, resolve_fleet_scope

router = APIRouter(prefix="/enterprise/fleet-memory", tags=["enterprise"])


class FleetRebuildBody(BaseModel):
    org_slug: str = Field(default="default", max_length=64)
    audit_run_id: str | None = None
    embedding_mode: str | None = Field(
        default=None,
        description="deterministic or ollama; default auto-selects ollama when LLM enabled",
    )


class FleetSyncBody(BaseModel):
    org_slug: str = Field(default="default", max_length=64)
    direction: str = Field(description="push or pull")
    generation_id: str | None = None


@router.get("/status")
def fleet_memory_status(_gate: EnterpriseDep) -> dict[str, Any]:
    ctx = get_auth_context()
    if ctx is None:
        raise HTTPException(
            status_code=401,
            detail=problem("unauthorized", "missing authenticated IAM context"),
        )
    org_scope = fleet_scope_hash(ctx.tenant_id)
    memory_store = build_memory_chunk_store(allow_in_memory=True)
    local_gen = None
    if memory_store is not None:
        local_gen = memory_store.latest_generation(
            org_scope_hash=org_scope, tenant_id=ctx.tenant_id
        )
    remote = fleet_memory_remote_status(org_scope_hash=org_scope)
    return {
        "tenant_id": str(ctx.tenant_id),
        "org_scope_hash": org_scope,
        "fleet_memory_enabled": enterprise_feature_enabled("fleet_memory"),
        "local_generation_id": str(local_gen.generation_id) if local_gen else None,
        "local_chunk_count": local_gen.chunk_count if local_gen else 0,
        "remote": remote,
    }


@router.post("/rebuild")
def fleet_memory_rebuild(
    body: FleetRebuildBody,
    _gate: EnterpriseDep,
    store: StoreDep,
) -> dict[str, Any]:
    ctx = get_auth_context()
    if ctx is None:
        raise HTTPException(status_code=401, detail=problem("unauthorized", "missing IAM context"))
    memory_store = build_memory_chunk_store(allow_in_memory=True)
    if memory_store is None:
        raise HTTPException(
            status_code=503,
            detail=problem("memory_store_unavailable", "memory chunk store is not configured"),
        )
    audit_uuid = UUID(body.audit_run_id) if body.audit_run_id else None
    conninfo = nimbusware_database_url()
    in_memory_rows = None
    if conninfo is None and hasattr(store, "list_all_event_rows"):
        in_memory_rows = store.list_all_event_rows()
    result = rebuild_fleet_memory_index(
        memory_store,
        tenant_id=ctx.tenant_id,
        org_slug=body.org_slug,
        embedding_mode=resolve_fleet_embedding_mode(body.embedding_mode),
        conninfo=conninfo,
        in_memory_event_rows=in_memory_rows,
        audit_store=store,
        audit_run_id=audit_uuid,
    )
    return {
        "tenant_id": str(result.tenant_id),
        "org_scope_hash": result.org_scope_hash,
        "generation_id": str(result.generation_id),
        "chunks_added": result.chunks_added,
        "chunks_skipped": result.chunks_skipped,
        "embedding_mode": resolve_fleet_embedding_mode(body.embedding_mode),
    }


@router.get("/search")
def fleet_memory_search(
    _gate: EnterpriseDep,
    q: Annotated[str, Query(min_length=1, max_length=512)],
    k: Annotated[int, Query(ge=1, le=20)] = 5,
    max_chars: Annotated[int, Query(ge=0, le=8000)] = 2000,
    embedding_mode: Annotated[str | None, Query()] = None,
) -> dict[str, Any]:
    ctx = get_auth_context()
    if ctx is None:
        raise HTTPException(status_code=401, detail=problem("unauthorized", "missing IAM context"))
    memory_store = build_memory_chunk_store(allow_in_memory=True)
    if memory_store is None:
        raise HTTPException(
            status_code=503,
            detail=problem("memory_store_unavailable", "memory chunk store is not configured"),
        )
    _, org_scope = resolve_fleet_scope(tenant_id=ctx.tenant_id)
    mode = resolve_fleet_embedding_mode(embedding_mode)
    hits = search_fleet_memory(
        memory_store,
        q,
        org_scope_hash=org_scope,
        tenant_id=ctx.tenant_id,
        k=k,
        embedding_mode=mode,
    )
    return {
        "org_scope_hash": org_scope,
        "query": q,
        "embedding_mode": mode,
        "hit_count": len(hits),
        "hits": [h.model_dump(mode="json") for h in hits],
        "excerpt": format_memory_excerpt(hits, max_chars=max_chars),
    }


@router.post("/sync")
def fleet_memory_sync(body: FleetSyncBody, _gate: EnterpriseDep) -> dict[str, Any]:
    ctx = get_auth_context()
    if ctx is None:
        raise HTTPException(status_code=401, detail=problem("unauthorized", "missing IAM context"))
    memory_store = build_memory_chunk_store(allow_in_memory=True)
    if memory_store is None:
        raise HTTPException(
            status_code=503,
            detail=problem("memory_store_unavailable", "memory chunk store is not configured"),
        )
    direction = body.direction.strip().lower()
    try:
        if direction == "push":
            out = push_fleet_memory_to_canonical(
                memory_store,
                tenant_id=ctx.tenant_id,
                org_slug=body.org_slug,
            )
        elif direction == "pull":
            out = pull_fleet_memory_from_canonical(
                memory_store,
                tenant_id=ctx.tenant_id,
                org_slug=body.org_slug,
                generation_id=body.generation_id,
            )
        else:
            raise HTTPException(
                status_code=422,
                detail=problem("invalid_direction", "direction must be push or pull"),
            )
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail=problem("fleet_sync_failed", str(exc)),
        ) from exc
    return out

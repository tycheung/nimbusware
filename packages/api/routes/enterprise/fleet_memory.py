from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from agent_tools.memory_bridge import try_broker_memory_search
from api.deps import StoreDep
from api.errors import problem
from api.routes.enterprise.core import EnterpriseDep
from api.schemas.peel_responses import memory_json_openapi_responses
from broker_client.flags import broker_memory_enabled
from broker_client.peel_assert import is_memory_store_or_miss
from memory.broker_route import (
    STATUS_PROBE_QUERY,
    broker_memory_hits,
    format_broker_memory_excerpt,
    map_broker_memory_http_miss,
    resolve_memory_store_or_miss,
)
from env.edition import enterprise_feature_enabled
from env.env_flags import nimbusware_database_url
from iam.context import get_auth_context
from memory.peel_fleet.index import rebuild_fleet_memory_index
from memory.peel_fleet.sync import (
    fleet_memory_remote_status,
    pull_fleet_memory_from_canonical,
    push_fleet_memory_to_canonical,
)
from memory.peel_index.embeddings import resolve_fleet_embedding_mode
from memory.peel_index.search import format_memory_excerpt, search_fleet_memory
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


class FleetMemoryStatusResponse(BaseModel):
    """GET /enterprise/fleet-memory/status (`sak480-e`)."""

    tenant_id: str | None = None
    org_scope_hash: str | None = None
    fleet_memory_enabled: bool | None = None
    local_generation_id: str | None = None
    local_chunk_count: int = 0
    remote: dict[str, Any] | None = None
    via: str | None = None
    error: str | None = None
    feature: str | None = None


class FleetMemorySearchResponse(BaseModel):
    """GET /enterprise/fleet-memory/search (`sak480-e`)."""

    org_scope_hash: str | None = None
    query: str | None = None
    embedding_mode: str | None = None
    hit_count: int = 0
    hits: list[dict[str, Any]] = Field(default_factory=list)
    excerpt: str | None = None
    via: str | None = None
    error: str | None = None
    feature: str | None = None


class FleetMemoryRebuildResponse(BaseModel):
    """POST /enterprise/fleet-memory/rebuild (`sak483-g`)."""

    model_config = {"extra": "allow"}

    tenant_id: str | None = None
    org_scope_hash: str | None = None
    generation_id: str | None = None
    chunks_added: int | None = None
    chunks_skipped: int | None = None
    embedding_mode: str | None = None
    via: str | None = None
    error: str | None = None
    feature: str | None = None


class FleetMemorySyncResponse(BaseModel):
    """POST /enterprise/fleet-memory/sync (`sak483-g`)."""

    model_config = {"extra": "allow"}

    via: str | None = None
    error: str | None = None
    feature: str | None = None


@router.get(
    "/status",
    response_model=FleetMemoryStatusResponse,
    response_model_exclude_none=True,
    summary="Fleet memory status (MEMORY peel-aware; sak480-e / sak493-i)",
    responses=memory_json_openapi_responses(),  # sak493-i / sak511-b
)
def fleet_memory_status(_gate: EnterpriseDep) -> dict[str, Any]:
    ctx = get_auth_context()
    if ctx is None:
        raise HTTPException(
            status_code=401,
            detail=problem("unauthorized", "missing authenticated IAM context"),
        )
    org_scope = fleet_scope_hash(ctx.tenant_id)
    status_base = {
        "tenant_id": str(ctx.tenant_id),
        "org_scope_hash": org_scope,
        "fleet_memory_enabled": enterprise_feature_enabled("fleet_memory"),
    }
    if broker_memory_enabled():
        try:
            probe = try_broker_memory_search(STATUS_PROBE_QUERY, limit=1)
            if isinstance(probe, dict):
                hits = broker_memory_hits(probe)
                return {
                    **status_base,
                    "via": "broker",
                    "local_generation_id": None,
                    "local_chunk_count": len(hits),
                    "remote": {"via": "broker", "configured": True},
                }
            return map_broker_memory_http_miss(
                RuntimeError(
                    "fleet memory status unavailable under NIMBUSWARE_BROKER_MEMORY=1|2"
                ),
                feature="fleet_memory_status",
                miss_extra={
                    **status_base,
                    "local_generation_id": None,
                    "local_chunk_count": 0,
                    "remote": None,
                },
            )
        except Exception as exc:  # noqa: BLE001 — sak493-i
            return map_broker_memory_http_miss(
                exc,
                feature="fleet_memory_status",
                miss_extra={
                    **status_base,
                    "local_generation_id": None,
                    "local_chunk_count": 0,
                    "remote": None,
                },
            )
    memory_store = resolve_memory_store_or_miss(
        feature="fleet_memory_status",
        local_only=True,
        allow_none=True,
    )
    local_gen = None
    if memory_store is not None:
        local_gen = memory_store.latest_generation(
            org_scope_hash=org_scope, tenant_id=ctx.tenant_id
        )
    remote = fleet_memory_remote_status(org_scope_hash=org_scope)
    return {
        **status_base,
        "local_generation_id": str(local_gen.generation_id) if local_gen else None,
        "local_chunk_count": local_gen.chunk_count if local_gen else 0,
        "remote": remote,
    }


@router.post(
    "/rebuild",
    response_model=FleetMemoryRebuildResponse,
    response_model_exclude_none=True,
    summary="Fleet memory rebuild (`sak483-g`; peel-aware `sak494-b`)",
    responses=memory_json_openapi_responses(),  # sak494-c
)
def fleet_memory_rebuild(
    body: FleetRebuildBody,
    _gate: EnterpriseDep,
    store: StoreDep,
) -> dict[str, Any]:
    ctx = get_auth_context()
    if ctx is None:
        raise HTTPException(status_code=401, detail=problem("unauthorized", "missing IAM context"))
    org_scope = fleet_scope_hash(ctx.tenant_id)
    resolved = resolve_memory_store_or_miss(
        feature="fleet_memory_rebuild",
        miss_extra={
            "tenant_id": str(ctx.tenant_id),
            "org_scope_hash": org_scope,
            "generation_id": None,
            "chunks_added": None,
            "chunks_skipped": None,
            "embedding_mode": body.embedding_mode,
        },
    )
    if is_memory_store_or_miss(resolved):
        return resolved
    memory_store = resolved
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


@router.get(
    "/search",
    response_model=FleetMemorySearchResponse,
    response_model_exclude_none=True,
    summary="Fleet memory search (MEMORY peel-aware; sak480-e / sak493-i)",
    responses=memory_json_openapi_responses(),  # sak493-i / sak511-b
)
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
    if broker_memory_enabled():
        org_scope = fleet_scope_hash(ctx.tenant_id)
        mode = embedding_mode or "broker"
        search_base = {
            "org_scope_hash": org_scope,
            "query": q,
            "embedding_mode": mode,
            "hit_count": 0,
            "hits": [],
            "excerpt": None,
        }
        try:
            broker_result = try_broker_memory_search(q, limit=k)
            if isinstance(broker_result, dict):
                hits = broker_memory_hits(broker_result)
                return {
                    **search_base,
                    "hit_count": len(hits),
                    "hits": hits,
                    "excerpt": format_broker_memory_excerpt(hits, max_chars=max_chars),
                    "via": "broker",
                }
            return map_broker_memory_http_miss(
                RuntimeError(
                    "fleet memory search unavailable under NIMBUSWARE_BROKER_MEMORY=1|2"
                ),
                feature="fleet_memory_search",
                miss_extra=search_base,
            )
        except Exception as exc:  # noqa: BLE001 — sak493-i
            return map_broker_memory_http_miss(
                exc,
                feature="fleet_memory_search",
                miss_extra=search_base,
            )
    _, org_scope = resolve_fleet_scope(tenant_id=ctx.tenant_id)
    mode = resolve_fleet_embedding_mode(embedding_mode)
    search_base = {
        "org_scope_hash": org_scope,
        "query": q,
        "embedding_mode": mode,
        "hit_count": 0,
        "hits": [],
        "excerpt": None,
    }
    memory_store = resolve_memory_store_or_miss(
        feature="fleet_memory_search",
        local_only=True,
    )
    hits = search_fleet_memory(
        memory_store,
        q,
        org_scope_hash=org_scope,
        tenant_id=ctx.tenant_id,
        k=k,
        embedding_mode=mode,
    )
    return {
        **search_base,
        "hit_count": len(hits),
        "hits": [h.model_dump(mode="json") for h in hits],
        "excerpt": format_memory_excerpt(hits, max_chars=max_chars),
    }


@router.post(
    "/sync",
    response_model=FleetMemorySyncResponse,
    response_model_exclude_none=True,
    summary="Fleet memory sync (`sak483-g`; peel-aware `sak494-b`)",
    responses=memory_json_openapi_responses(),  # sak494-c
)
def fleet_memory_sync(body: FleetSyncBody, _gate: EnterpriseDep) -> dict[str, Any]:
    ctx = get_auth_context()
    if ctx is None:
        raise HTTPException(status_code=401, detail=problem("unauthorized", "missing IAM context"))
    resolved = resolve_memory_store_or_miss(
        feature="fleet_memory_sync",
        miss_extra={"direction": body.direction.strip().lower()},
    )
    if is_memory_store_or_miss(resolved):
        return resolved
    memory_store = resolved
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

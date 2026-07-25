from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from api.deps import ProjectStoreDep
from api.errors import problem
from api.schemas.openapi import PROBLEM_RESPONSE_404
from api.schemas.peel_responses import memory_json_openapi_responses
from api.user import UserDep
from memory.broker_route import require_local_memory_chunk_store
from memory.peel_index.repo_scope import repo_scope_hash

router = APIRouter(prefix="/memory", tags=["memory"])


class MemoryChunksResponse(BaseModel):
    """GET /memory/chunks (`sak480-e`)."""

    project_id: str | None = None
    repo_scope_hash: str | None = None
    workspace_path: str | None = None
    chunks: list[dict[str, Any]] = Field(default_factory=list)
    total: int = 0
    caption: str | None = None
    via: str | None = None
    error: str | None = None
    feature: str | None = None


def _chunk_preview(record: Any, *, max_chars: int = 240) -> dict[str, Any]:
    full = str(record.excerpt or "")
    excerpt = full
    if len(excerpt) > max_chars:
        excerpt = excerpt[: max_chars - 1] + "…"
    return {
        "chunk_id": str(record.chunk_id),
        "run_id": str(record.run_id),
        "source_event_type": record.source_event_type,
        "category": record.category,
        "severity": record.severity,
        "excerpt": excerpt,
        "excerpt_len": len(full),
    }


@router.get(
    "/chunks",
    response_model=MemoryChunksResponse,
    response_model_exclude_none=True,
    responses={
        **memory_json_openapi_responses(not_found=PROBLEM_RESPONSE_404),  # sak498-b
    },
    summary="List memory chunks (`sak480-e`; peel-aware `sak498-b`)",
)
def list_memory_chunks(
    project_id: Annotated[UUID, Query(description="Project whose workspace defines repo scope")],
    store: ProjectStoreDep,
    _user: UserDep,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> dict[str, Any]:
    record = store.get(project_id)
    if record is None:
        raise HTTPException(
            status_code=404,
            detail=problem("project_not_found", f"Unknown project id: {project_id}"),
        )
    ws = Path(str(record.workspace_path))
    scope = repo_scope_hash(ws)
    store_or_miss = require_local_memory_chunk_store(
        feature="memory_chunks_list",
        miss_extra={
            "project_id": str(project_id),
            "repo_scope_hash": scope,
            "workspace_path": str(ws),
            "chunks": [],
            "total": 0,
        },
    )
    if isinstance(store_or_miss, dict):
        return store_or_miss
    memory_store = store_or_miss
    if memory_store is None:
        return {
            "project_id": str(project_id),
            "repo_scope_hash": scope,
            "workspace_path": str(ws),
            "chunks": [],
            "total": 0,
            "caption": "Memory chunk store is not configured.",
        }
    rows = memory_store.list_chunks_for_scope(scope)
    previews = [_chunk_preview(ch) for ch in rows[:limit]]
    return {
        "project_id": str(project_id),
        "repo_scope_hash": scope,
        "workspace_path": str(ws),
        "chunks": previews,
        "total": len(rows),
        "caption": f"{len(rows)} chunk(s) indexed for this workspace scope.",
    }

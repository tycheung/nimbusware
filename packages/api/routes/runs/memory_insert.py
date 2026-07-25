from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.deps import OrchDep, ProjectStoreDep, StoreDep
from api.errors import problem
from api.schemas.openapi import PROBLEM_RESPONSE_404, PROBLEM_RESPONSE_422
from api.schemas.peel_responses import memory_json_openapi_responses
from maker.workspace.workspace import (
    project_id_from_run_created_metadata,
    run_created_metadata_from_rows,
)
from memory.broker_route import require_local_memory_chunk_store
from memory.peel_index.repo_scope import repo_scope_hash
from orchestrator.memory_run_insert import (
    find_memory_chunk_for_scope,
    insert_memory_chunk_into_run,
)

router = APIRouter()


class MemoryChunkInsertResponse(BaseModel):
    """POST /runs/{run_id}/memory-chunks/{chunk_id}/insert (`sak487-e`)."""

    model_config = {"extra": "allow"}

    run_id: str | None = None
    chunk_id: str | None = None
    category: str | None = None
    severity: str | None = None
    via: str | None = None
    error: str | None = None
    feature: str | None = None


@router.post(
    "/runs/{run_id}/memory-chunks/{chunk_id}/insert",
    response_model=MemoryChunkInsertResponse,
    response_model_exclude_none=True,
    responses={
        **memory_json_openapi_responses(not_found=PROBLEM_RESPONSE_404),  # sak496-f / sak498-b
        422: PROBLEM_RESPONSE_422,
    },
)
def post_insert_memory_chunk(
    run_id: UUID,
    chunk_id: UUID,
    store: StoreDep,
    project_store: ProjectStoreDep,
    _orch: OrchDep,
) -> dict[str, Any]:
    rows = store.list_run_events(str(run_id))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(run_id)}),
        )
    meta = run_created_metadata_from_rows(rows)
    project_id_raw = project_id_from_run_created_metadata(meta)
    if project_id_raw is None:
        raise HTTPException(
            status_code=422,
            detail=problem("invalid_request", "run has no project_id; cannot resolve memory scope"),
        )
    project = project_store.get(UUID(project_id_raw))
    if project is None:
        raise HTTPException(
            status_code=404,
            detail=problem("project_not_found", f"Unknown project id: {project_id_raw}"),
        )
    store_or_miss = require_local_memory_chunk_store(
        feature="memory_chunk_insert",
        miss_extra={"run_id": str(run_id), "chunk_id": str(chunk_id)},
    )
    if isinstance(store_or_miss, dict):
        return store_or_miss
    memory_store = store_or_miss
    if memory_store is None:
        raise HTTPException(
            status_code=422,
            detail=problem("invalid_request", "memory chunk store is not configured"),
        )
    scope = repo_scope_hash(Path(str(project.workspace_path)))
    chunk = find_memory_chunk_for_scope(memory_store, repo_scope_hash=scope, chunk_id=chunk_id)
    if chunk is None:
        raise HTTPException(
            status_code=404,
            detail=problem(
                "chunk_not_found",
                "memory chunk not found for run workspace scope",
                details={"chunk_id": str(chunk_id)},
            ),
        )
    result = insert_memory_chunk_into_run(store, run_id=run_id, chunk=chunk)
    return {"run_id": str(run_id), **{k: str(v) for k, v in result.items()}}

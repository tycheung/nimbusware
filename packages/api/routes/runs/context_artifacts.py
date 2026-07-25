from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.deps import StoreDep
from api.errors import problem
from api.schemas.openapi import PROBLEM_RESPONSE_404, PROBLEM_RESPONSE_422
from api.schemas.peel_responses import memory_json_openapi_responses
from maker.workspace.workspace import (
    project_id_from_run_created_metadata,
    run_created_metadata_from_rows,
)
from orchestrator.context_artifacts import (
    create_context_artifact_from_compaction,
    get_context_artifact,
    insert_context_artifact_into_run,
)

router = APIRouter()


class ContextArtifactFromCompactionBody(BaseModel):
    title: str | None = None


class ContextArtifactFromCompactionResponse(BaseModel):
    """POST context-artifacts/from-compaction (`sak486-g`)."""

    model_config = {"extra": "allow"}

    run_id: str | None = None
    project_id: str | None = None
    artifact_id: str | None = None
    title: str | None = None
    kind: str | None = None
    via: str | None = None
    error: str | None = None
    feature: str | None = None


class ContextArtifactInsertResponse(BaseModel):
    """POST context-artifacts/{id}/insert (`sak486-g`)."""

    model_config = {"extra": "allow"}

    run_id: str | None = None
    artifact_id: str | None = None
    title: str | None = None
    kind: str | None = None
    via: str | None = None
    error: str | None = None
    feature: str | None = None


@router.post(
    "/runs/{run_id}/context-artifacts/from-compaction",
    response_model=ContextArtifactFromCompactionResponse,
    response_model_exclude_none=True,
    responses={
        **memory_json_openapi_responses(not_found=PROBLEM_RESPONSE_404),  # sak498-e
        422: PROBLEM_RESPONSE_422,
    },
)
def post_context_artifact_from_compaction(
    run_id: UUID,
    store: StoreDep,
    body: ContextArtifactFromCompactionBody | None = None,
) -> dict[str, str]:
    rows = store.list_run_events(str(run_id))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(run_id)}),
        )
    meta = run_created_metadata_from_rows(rows)
    project_id = project_id_from_run_created_metadata(meta)
    if project_id is None:
        raise HTTPException(
            status_code=422,
            detail=problem("invalid_request", "run has no project_id; cannot save artifact"),
        )
    title = body.title if body is not None else None
    try:
        artifact = create_context_artifact_from_compaction(
            project_id=project_id,
            rows=rows,
            title=title,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=problem("invalid_request", str(exc)),
        ) from exc
    return {
        "run_id": str(run_id),
        "project_id": str(project_id),
        "artifact_id": artifact.artifact_id,
        "title": artifact.title,
        "kind": artifact.kind,
    }


@router.post(
    "/runs/{run_id}/context-artifacts/{artifact_id}/insert",
    response_model=ContextArtifactInsertResponse,
    response_model_exclude_none=True,
    responses={
        **memory_json_openapi_responses(not_found=PROBLEM_RESPONSE_404),  # sak498-e
        422: PROBLEM_RESPONSE_422,
    },
)
def post_insert_context_artifact(
    run_id: UUID,
    artifact_id: str,
    store: StoreDep,
) -> dict[str, str]:
    rows = store.list_run_events(str(run_id))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(run_id)}),
        )
    meta = run_created_metadata_from_rows(rows)
    project_id = project_id_from_run_created_metadata(meta)
    if project_id is None:
        raise HTTPException(
            status_code=422,
            detail=problem("invalid_request", "run has no project_id; cannot resolve artifacts"),
        )
    artifact = get_context_artifact(project_id, artifact_id)
    if artifact is None:
        raise HTTPException(
            status_code=404,
            detail=problem(
                "artifact_not_found",
                "context artifact not found",
                details={"artifact_id": artifact_id.strip()},
            ),
        )
    result = insert_context_artifact_into_run(
        store,
        run_id=run_id,
        artifact=artifact,
    )
    return {"run_id": str(run_id), **{k: str(v) for k, v in result.items()}}

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from nimbusware_api.access import assert_project_accessible
from nimbusware_api.deps import ProjectStoreDep
from nimbusware_api.errors import problem
from nimbusware_api.schemas.openapi import PROBLEM_RESPONSE_404, PROBLEM_RESPONSE_422
from nimbusware_api.user import UserDep
from nimbusware_orchestrator.context_artifacts import (
    ContextArtifactRecord,
    bridge_artifact_to_memory_index,
    create_context_artifact,
    get_context_artifact,
    list_context_artifacts,
)

router = APIRouter(prefix="/projects", tags=["projects"])


class ContextArtifactResponse(BaseModel):
    artifact_id: str
    project_id: str
    title: str
    content: str
    kind: str
    created_at: str


class ContextArtifactListResponse(BaseModel):
    project_id: str
    artifacts: list[ContextArtifactResponse] = Field(default_factory=list)
    count: int = 0


class ContextArtifactCreateBody(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    content: str = Field(min_length=1, max_length=32000)
    kind: str = Field(default="note", max_length=64)


def _to_response(record: ContextArtifactRecord) -> ContextArtifactResponse:
    return ContextArtifactResponse(**record.to_dict())


@router.get(
    "/{project_id}/context-artifacts",
    response_model=ContextArtifactListResponse,
    responses={404: PROBLEM_RESPONSE_404},
)
def get_project_context_artifacts(
    project_id: UUID,
    store: ProjectStoreDep,
    _user: UserDep,
) -> ContextArtifactListResponse:
    record = store.get(project_id)
    if record is None:
        raise HTTPException(
            status_code=404,
            detail=problem("project_not_found", f"Unknown project id: {project_id}"),
        )
    assert_project_accessible(record)
    rows = list_context_artifacts(project_id)
    return ContextArtifactListResponse(
        project_id=str(project_id),
        artifacts=[_to_response(r) for r in rows],
        count=len(rows),
    )


@router.post(
    "/{project_id}/context-artifacts",
    response_model=ContextArtifactResponse,
    responses={404: PROBLEM_RESPONSE_404, 422: PROBLEM_RESPONSE_422},
)
def post_project_context_artifact(
    project_id: UUID,
    body: ContextArtifactCreateBody,
    store: ProjectStoreDep,
    _user: UserDep,
) -> ContextArtifactResponse:
    record = store.get(project_id)
    if record is None:
        raise HTTPException(
            status_code=404,
            detail=problem("project_not_found", f"Unknown project id: {project_id}"),
        )
    assert_project_accessible(record)
    try:
        created = create_context_artifact(
            project_id=project_id,
            title=body.title,
            content=body.content,
            kind=body.kind,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=problem("invalid_request", str(exc)),
        ) from exc
    return _to_response(created)


class ContextArtifactBridgeResponse(BaseModel):
    project_id: str
    artifact_id: str
    bridge_path: str
    indexed: bool = False


@router.post(
    "/{project_id}/context-artifacts/{artifact_id}/bridge-memory",
    response_model=ContextArtifactBridgeResponse,
    responses={404: PROBLEM_RESPONSE_404},
)
def bridge_context_artifact_to_memory(
    project_id: UUID,
    artifact_id: str,
    store: ProjectStoreDep,
    _user: UserDep,
) -> ContextArtifactBridgeResponse:
    record = store.get(project_id)
    if record is None:
        raise HTTPException(
            status_code=404,
            detail=problem("project_not_found", f"Unknown project id: {project_id}"),
        )
    assert_project_accessible(record)
    artifact = get_context_artifact(project_id, artifact_id)
    if artifact is None:
        raise HTTPException(
            status_code=404,
            detail=problem(
                "artifact_not_found",
                "context artifact not found",
                details={"artifact_id": artifact_id},
            ),
        )
    bridge = bridge_artifact_to_memory_index(artifact)
    return ContextArtifactBridgeResponse(
        project_id=str(project_id),
        artifact_id=artifact.artifact_id,
        bridge_path=bridge["bridge_path"],
        indexed=True,
    )

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from api.access import assert_project_accessible
from api.deps import ProjectStoreDep
from api.errors import problem
from api.schemas.openapi import PROBLEM_RESPONSE_404, PROBLEM_RESPONSE_422
from api.schemas.peel_responses import memory_json_openapi_responses, with_long_tail_peel_503
from api.user import UserDep, maker_user_id_str
from orchestrator.context_artifacts import (
    ContextArtifactRecord,
    bridge_artifact_to_memory_index,
    create_context_artifact,
    get_context_artifact,
    list_context_artifacts_for_actor,
)

router = APIRouter(prefix="/projects", tags=["projects"])


class ContextArtifactResponse(BaseModel):
    artifact_id: str
    project_id: str
    title: str
    content: str
    kind: str
    created_at: str
    owner_user_id: str = ""
    visibility: str = "private"


class ContextArtifactListResponse(BaseModel):
    project_id: str
    artifacts: list[ContextArtifactResponse] = Field(default_factory=list)
    count: int = 0


class ContextArtifactCreateBody(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    content: str = Field(min_length=1, max_length=32000)
    kind: str = Field(default="note", max_length=64)
    visibility: str = Field(default="private", max_length=32)


def _to_response(record: ContextArtifactRecord) -> ContextArtifactResponse:
    return ContextArtifactResponse(**record.to_dict())


@router.get(
    "/{project_id}/context-artifacts",
    response_model=ContextArtifactListResponse,
    responses=with_long_tail_peel_503({404: PROBLEM_RESPONSE_404}),  # sak516-a
)
def get_project_context_artifacts(
    project_id: UUID,
    store: ProjectStoreDep,
    request: Request,
    _user: UserDep,
) -> ContextArtifactListResponse:
    record = store.get(project_id)
    if record is None:
        raise HTTPException(
            status_code=404,
            detail=problem("project_not_found", f"Unknown project id: {project_id}"),
        )
    assert_project_accessible(record)
    actor = maker_user_id_str(request)
    rows = list_context_artifacts_for_actor(project_id, actor)
    return ContextArtifactListResponse(
        project_id=str(project_id),
        artifacts=[_to_response(r) for r in rows],
        count=len(rows),
    )


@router.post(
    "/{project_id}/context-artifacts",
    response_model=ContextArtifactResponse,
    responses=with_long_tail_peel_503(
        {404: PROBLEM_RESPONSE_404, 422: PROBLEM_RESPONSE_422},
    ),  # sak516-b
)
def post_project_context_artifact(
    project_id: UUID,
    body: ContextArtifactCreateBody,
    store: ProjectStoreDep,
    request: Request,
    _user: UserDep,
) -> ContextArtifactResponse:
    record = store.get(project_id)
    if record is None:
        raise HTTPException(
            status_code=404,
            detail=problem("project_not_found", f"Unknown project id: {project_id}"),
        )
    assert_project_accessible(record)
    owner = maker_user_id_str(request)
    visibility = (body.visibility or "private").strip().lower()
    if visibility not in ("private", "project", "shared"):
        visibility = "private"
    try:
        created = create_context_artifact(
            project_id=project_id,
            title=body.title,
            content=body.content,
            kind=body.kind,
            owner_user_id=owner,
            visibility=visibility,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=problem("invalid_request", str(exc)),
        ) from exc
    return _to_response(created)


class ContextArtifactBridgeResponse(BaseModel):
    model_config = {"extra": "allow"}

    project_id: str
    artifact_id: str
    bridge_path: str = ""
    indexed: bool = False
    via: str | None = None
    error: str | None = None
    feature: str | None = None
    status: str | None = None


@router.post(
    "/{project_id}/context-artifacts/{artifact_id}/bridge-memory",
    response_model=ContextArtifactBridgeResponse,
    response_model_exclude_none=True,
    responses={
        **memory_json_openapi_responses(not_found=PROBLEM_RESPONSE_404),  # sak499-c
    },
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
    try:
        bridge = bridge_artifact_to_memory_index(artifact)
    except RuntimeError as exc:
        from broker_client.flags import broker_memory_enabled

        if not broker_memory_enabled():
            raise
        from memory.broker_route import map_broker_memory_http_miss

        miss = map_broker_memory_http_miss(
            exc,
            feature="context_artifact_bridge",
            miss_extra={
                "project_id": str(project_id),
                "artifact_id": artifact_id,
            },
        )
        return ContextArtifactBridgeResponse(
            project_id=str(project_id),
            artifact_id=artifact_id,
            bridge_path="",
            indexed=False,
            via=miss.get("via"),
            error=miss.get("error"),
            feature=miss.get("feature"),
            status=miss.get("status"),
        )
    return ContextArtifactBridgeResponse(
        project_id=str(project_id),
        artifact_id=artifact.artifact_id,
        bridge_path=bridge["bridge_path"],
        indexed=True,
    )

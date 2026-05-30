"""Maker project CRUD API (fo301)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from nimbusware_api.admin import AdminDep
from nimbusware_api.deps import ProjectStoreDep
from nimbusware_api.errors import problem
from nimbusware_api.schemas.openapi import (
    PROBLEM_RESPONSE_404,
    PROBLEM_RESPONSE_422,
    PROBLEM_RESPONSE_500,
)
from nimbusware_maker.models import ATTACH_TEMPLATE, PROJECT_TEMPLATES

router = APIRouter(prefix="/projects", tags=["projects"])


class ProjectResponse(BaseModel):
    project_id: str
    name: str
    workspace_path: str
    template: str
    default_workflow_profile: str
    created_at: str
    tenant_id: str


class ProjectListResponse(BaseModel):
    projects: list[ProjectResponse]


class ProjectCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    workspace_path: str = Field(min_length=1, max_length=4096)
    template: str = Field(default=ATTACH_TEMPLATE, max_length=32)
    default_workflow_profile: str = Field(default="micro_slice", min_length=1, max_length=120)


def _to_response(record: object) -> ProjectResponse:
    data = record.to_dict()  # type: ignore[attr-defined]
    return ProjectResponse(**data)


@router.get("", response_model=ProjectListResponse)
def list_projects(store: ProjectStoreDep) -> ProjectListResponse:
    return ProjectListResponse(projects=[_to_response(p) for p in store.list()])


@router.get("/{project_id}", response_model=ProjectResponse, responses={404: PROBLEM_RESPONSE_404})
def get_project(project_id: UUID, store: ProjectStoreDep) -> ProjectResponse:
    record = store.get(project_id)
    if record is None:
        raise HTTPException(
            status_code=404,
            detail=problem("project_not_found", f"Unknown project id: {project_id}"),
        )
    return _to_response(record)


@router.post(
    "",
    response_model=ProjectResponse,
    responses={422: PROBLEM_RESPONSE_422, 500: PROBLEM_RESPONSE_500},
)
def create_project(
    body: ProjectCreateRequest,
    store: ProjectStoreDep,
    _admin: AdminDep,
) -> ProjectResponse:
    if body.template.strip().lower() not in PROJECT_TEMPLATES:
        raise HTTPException(
            status_code=422,
            detail=problem(
                "invalid_request",
                f"template must be one of {sorted(PROJECT_TEMPLATES)}",
            ),
        )
    try:
        record = store.create(
            name=body.name,
            workspace_path=body.workspace_path,
            template=body.template,
            default_workflow_profile=body.default_workflow_profile,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=problem("invalid_request", str(exc)),
        ) from exc
    return _to_response(record)


@router.delete(
    "/{project_id}",
    status_code=204,
    responses={404: PROBLEM_RESPONSE_404},
)
def delete_project(project_id: UUID, store: ProjectStoreDep, _admin: AdminDep) -> None:
    if not store.delete(project_id):
        raise HTTPException(
            status_code=404,
            detail=problem("project_not_found", f"Unknown project id: {project_id}"),
        )

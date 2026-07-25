from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.admin import AdminDep
from api.deps import ProjectStoreDep
from api.errors import problem
from api.schemas.peel_responses import (
    DeleteOkResponse,
    long_tail_json_openapi_responses,
    with_long_tail_peel_503,
)
from api.schemas.openapi import (
    PROBLEM_RESPONSE_404,
    PROBLEM_RESPONSE_422,
    PROBLEM_RESPONSE_500,
)
from api.user import UserDep
from env.edition import is_enterprise
from iam.context import resolve_store_tenant_id
from maker.models import ATTACH_TEMPLATE, PROJECT_TEMPLATES

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


class ProjectUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    workspace_path: str | None = Field(default=None, min_length=1, max_length=4096)
    default_workflow_profile: str | None = Field(default=None, min_length=1, max_length=120)


def _to_response(record: object) -> ProjectResponse:
    data = record.to_dict()  # type: ignore[attr-defined]
    return ProjectResponse(**data)


@router.get(
    "",
    response_model=ProjectListResponse,
    responses=long_tail_json_openapi_responses(),  # sak500-i
)
def list_projects(store: ProjectStoreDep, _user: UserDep) -> ProjectListResponse:
    tenant_id = resolve_store_tenant_id() if is_enterprise() else None
    rows = store.list(tenant_id=tenant_id) if tenant_id is not None else store.list()
    return ProjectListResponse(projects=[_to_response(p) for p in rows])


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
    responses=with_long_tail_peel_503({404: PROBLEM_RESPONSE_404}),  # sak512-g
)
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
    responses=with_long_tail_peel_503(
        {422: PROBLEM_RESPONSE_422, 500: PROBLEM_RESPONSE_500},
    ),  # sak512-g
)
def create_project(
    body: ProjectCreateRequest,
    store: ProjectStoreDep,
    _user: UserDep,
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
            tenant_id=resolve_store_tenant_id(),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=problem("invalid_request", str(exc)),
        ) from exc
    return _to_response(record)


@router.patch(
    "/{project_id}",
    response_model=ProjectResponse,
    responses=with_long_tail_peel_503(
        {404: PROBLEM_RESPONSE_404, 422: PROBLEM_RESPONSE_422},
    ),  # sak512-h
)
def update_project(
    project_id: UUID,
    body: ProjectUpdateRequest,
    store: ProjectStoreDep,
    _user: UserDep,
) -> ProjectResponse:
    if body.name is None and body.workspace_path is None and body.default_workflow_profile is None:
        raise HTTPException(
            status_code=422,
            detail=problem("invalid_request", "at least one field required"),
        )
    try:
        record = store.update(
            project_id,
            name=body.name,
            workspace_path=body.workspace_path,
            default_workflow_profile=body.default_workflow_profile,
        )
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=problem("project_not_found", f"Unknown project id: {project_id}"),
        ) from None
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=problem("invalid_request", str(exc)),
        ) from exc
    return _to_response(record)


@router.delete(
    "/{project_id}",
    response_model=DeleteOkResponse,
    response_model_exclude_none=True,
    responses=with_long_tail_peel_503({404: PROBLEM_RESPONSE_404}),  # sak512-h
)
def delete_project(project_id: UUID, store: ProjectStoreDep, _admin: AdminDep) -> DeleteOkResponse:
    if not store.delete(project_id):
        raise HTTPException(
            status_code=404,
            detail=problem("project_not_found", f"Unknown project id: {project_id}"),
        )
    return DeleteOkResponse(ok=True)

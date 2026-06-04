from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from nimbusware_api.deps import OrchDep, StoreDep
from nimbusware_api.errors import problem
from nimbusware_api.schemas.openapi import PROBLEM_RESPONSE_404, PROBLEM_RESPONSE_422
from nimbusware_maker.approval import last_git_commit_from_rows
from nimbusware_maker.slice_workflow import (
    apply_pending_slice,
    approve_run_plan,
    get_pending_state,
    prepare_next_pending_slice,
    revert_workspace,
    skip_pending_slice,
)

router = APIRouter()


class PendingSliceResponse(BaseModel):
    plan_approved: bool
    awaiting_approval: bool
    pending: dict[str, Any] | None = None
    last_snapshot: dict[str, Any] | None = None


@router.get(
    "/runs/{run_id}/maker/git-status",
    responses={404: PROBLEM_RESPONSE_404},
)
def get_maker_git_status(run_id: UUID, store: StoreDep) -> dict[str, Any]:
    rows = store.list_run_events(str(run_id))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(run_id)}),
        )
    commit = last_git_commit_from_rows(rows)
    return {"run_id": str(run_id), "git_commit": commit}


@router.get(
    "/runs/{run_id}/maker/pending",
    response_model=PendingSliceResponse,
    responses={404: PROBLEM_RESPONSE_404},
)
def get_maker_pending(run_id: UUID, orch: OrchDep, store: StoreDep) -> PendingSliceResponse:
    rows = store.list_run_events(str(run_id))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(run_id)}),
        )
    body = get_pending_state(orch, run_id)
    return PendingSliceResponse.model_validate(body)


@router.post(
    "/runs/{run_id}/maker/plan/approve",
    responses={404: PROBLEM_RESPONSE_404, 422: PROBLEM_RESPONSE_422},
)
def post_maker_plan_approve(run_id: UUID, orch: OrchDep, store: StoreDep) -> dict[str, str]:
    rows = store.list_run_events(str(run_id))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(run_id)}),
        )
    try:
        return approve_run_plan(orch, run_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=problem("invalid_request", str(exc)),
        ) from exc


@router.post(
    "/runs/{run_id}/maker/slices/prepare",
    responses={404: PROBLEM_RESPONSE_404, 422: PROBLEM_RESPONSE_422},
)
def post_maker_slice_prepare(run_id: UUID, orch: OrchDep, store: StoreDep) -> dict[str, Any]:
    rows = store.list_run_events(str(run_id))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(run_id)}),
        )
    try:
        return prepare_next_pending_slice(orch, run_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=problem("invalid_request", str(exc)),
        ) from exc


class SliceActionBody(BaseModel):
    slice_id: str = Field(min_length=1, max_length=120)


@router.post(
    "/runs/{run_id}/maker/slices/apply",
    responses={404: PROBLEM_RESPONSE_404, 422: PROBLEM_RESPONSE_422},
)
def post_maker_slice_apply(
    run_id: UUID,
    body: SliceActionBody,
    orch: OrchDep,
    store: StoreDep,
) -> dict[str, Any]:
    rows = store.list_run_events(str(run_id))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(run_id)}),
        )
    try:
        return apply_pending_slice(orch, run_id, body.slice_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=problem("invalid_request", str(exc)),
        ) from exc


@router.post(
    "/runs/{run_id}/maker/slices/skip",
    responses={404: PROBLEM_RESPONSE_404, 422: PROBLEM_RESPONSE_422},
)
def post_maker_slice_skip(
    run_id: UUID,
    body: SliceActionBody,
    orch: OrchDep,
    store: StoreDep,
) -> dict[str, Any]:
    rows = store.list_run_events(str(run_id))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(run_id)}),
        )
    try:
        return skip_pending_slice(orch, run_id, body.slice_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=problem("invalid_request", str(exc)),
        ) from exc


@router.post(
    "/runs/{run_id}/workspace/revert",
    responses={404: PROBLEM_RESPONSE_404, 422: PROBLEM_RESPONSE_422},
)
def post_workspace_revert(run_id: UUID, orch: OrchDep, store: StoreDep) -> dict[str, Any]:
    rows = store.list_run_events(str(run_id))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(run_id)}),
        )
    try:
        return revert_workspace(orch, run_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=problem("invalid_request", str(exc)),
        ) from exc

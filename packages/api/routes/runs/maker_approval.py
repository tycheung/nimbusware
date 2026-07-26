from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.deps import OrchDep, StoreDep
from api.errors import problem
from api.schemas.openapi import PROBLEM_RESPONSE_404, PROBLEM_RESPONSE_422
from api.schemas.peel_responses import llm_json_openapi_responses, with_long_tail_peel_503
from maker.approval import git_outputs_from_rows, last_git_commit_from_rows
from maker.slice_workflow import (
    apply_pending_slice,
    approve_run_plan,
    get_pending_state,
    prepare_next_pending_slice,
    revert_workspace,
    skip_pending_slice,
)
from maker.workspace.workspace import resolve_run_workspace
from orchestrator.git_outputs import maybe_open_gh_pr, run_branch_name

router = APIRouter()


class PendingSliceResponse(BaseModel):
    plan_approved: bool
    awaiting_approval: bool
    pending: dict[str, Any] | None = None
    last_snapshot: dict[str, Any] | None = None


class LaunchEvalResponse(BaseModel):
    """POST /runs/{id}/maker/launch-eval (`sak482-f`)."""

    model_config = {"extra": "allow"}

    via: str | None = None
    error: str | None = None
    feature: str | None = None


class MakerGitStatusResponse(BaseModel):
    """GET /runs/{id}/maker/git-status (`sak483-g`)."""

    model_config = {"extra": "allow"}

    run_id: str | None = None
    git_commit: dict[str, Any] | None = None
    git_outputs: dict[str, Any] | None = None
    via: str | None = None
    error: str | None = None
    feature: str | None = None


class MakerOpenPrResponse(BaseModel):
    """POST /runs/{id}/maker/open-pr (`sak483-g`)."""

    model_config = {"extra": "allow"}

    run_id: str | None = None
    pr: dict[str, Any] | None = None
    via: str | None = None
    error: str | None = None
    feature: str | None = None


class MakerActionResponse(BaseModel):
    """Maker workflow POST actions (`sak483-g`)."""

    model_config = {"extra": "allow"}

    via: str | None = None
    error: str | None = None
    feature: str | None = None


class MakerRunTestsResponse(BaseModel):
    """POST /runs/{id}/maker/run-tests (`sak483-g`)."""

    model_config = {"extra": "allow"}

    tests_passed: bool | None = None
    exit_code: int | None = None
    detail: str | None = None
    targets: list[str] | None = None
    via: str | None = None
    error: str | None = None
    feature: str | None = None


@router.get(
    "/runs/{run_id}/maker/git-status",
    response_model=MakerGitStatusResponse,
    summary="Maker git status (`sak483-g`)",
    responses=with_long_tail_peel_503({404: PROBLEM_RESPONSE_404}),  # sak507-a
)
def get_maker_git_status(run_id: UUID, store: StoreDep) -> dict[str, Any]:
    rows = store.list_run_events(str(run_id))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(run_id)}),
        )
    commit = last_git_commit_from_rows(rows)
    outputs = git_outputs_from_rows(rows)
    if not outputs.get("branch"):
        outputs["branch"] = run_branch_name(run_id)
    return {"run_id": str(run_id), "git_commit": commit, "git_outputs": outputs}


@router.post(
    "/runs/{run_id}/maker/open-pr",
    response_model=MakerOpenPrResponse,
    response_model_exclude_none=True,
    summary="Maker open PR (`sak483-g`)",
    responses=with_long_tail_peel_503(  # sak507-g
        {404: PROBLEM_RESPONSE_404, 422: PROBLEM_RESPONSE_422},
    ),
)
def post_maker_open_pr(run_id: UUID, store: StoreDep) -> dict[str, Any]:
    rows = store.list_run_events(str(run_id))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(run_id)}),
        )
    workspace = resolve_run_workspace(rows)
    if workspace is None:
        raise HTTPException(
            status_code=422,
            detail=problem("invalid_request", "run has no project workspace"),
        )
    result = maybe_open_gh_pr(workspace, run_id)
    if result.get("status") not in {"created", "skipped"}:
        raise HTTPException(
            status_code=422,
            detail=problem(
                "git_pr_failed", str(result.get("reason") or result.get("stderr") or result)
            ),
        )
    return {"run_id": str(run_id), "pr": result}


@router.get(
    "/runs/{run_id}/maker/pending",
    response_model=PendingSliceResponse,
    responses=with_long_tail_peel_503({404: PROBLEM_RESPONSE_404}),  # sak507-a
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
    response_model=MakerActionResponse,
    response_model_exclude_none=True,
    summary="Maker plan approve (`sak483-g`)",
    responses=with_long_tail_peel_503(  # sak507-b
        {404: PROBLEM_RESPONSE_404, 422: PROBLEM_RESPONSE_422},
    ),
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
    response_model=MakerActionResponse,
    response_model_exclude_none=True,
    summary="Maker slice prepare (`sak483-g`)",
    responses=with_long_tail_peel_503(  # sak507-b
        {404: PROBLEM_RESPONSE_404, 422: PROBLEM_RESPONSE_422},
    ),
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
    response_model=MakerActionResponse,
    response_model_exclude_none=True,
    summary="Maker slice apply (`sak483-g`)",
    responses=with_long_tail_peel_503(  # sak507-g
        {404: PROBLEM_RESPONSE_404, 422: PROBLEM_RESPONSE_422},
    ),
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
    response_model=MakerActionResponse,
    response_model_exclude_none=True,
    summary="Maker slice skip (`sak483-g`)",
    responses=with_long_tail_peel_503(  # sak507-h
        {404: PROBLEM_RESPONSE_404, 422: PROBLEM_RESPONSE_422},
    ),
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
    response_model=MakerActionResponse,
    response_model_exclude_none=True,
    summary="Workspace revert (`sak483-g`)",
    responses=with_long_tail_peel_503(  # sak507-h
        {404: PROBLEM_RESPONSE_404, 422: PROBLEM_RESPONSE_422},
    ),
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


@router.post(
    "/runs/{run_id}/maker/run-tests",
    response_model=MakerRunTestsResponse,
    response_model_exclude_none=True,
    summary="Maker run tests (`sak483-g`)",
    responses=with_long_tail_peel_503(  # sak507-i
        {404: PROBLEM_RESPONSE_404, 422: PROBLEM_RESPONSE_422},
    ),
)
def post_maker_run_tests(run_id: UUID, store: StoreDep) -> dict[str, Any]:
    rows = store.list_run_events(str(run_id))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(run_id)}),
        )
    from maker.workspace.workspace import resolve_run_workspace
    from orchestrator.patch_context import (
        patch_context_from_run_rows,
        resolve_patch_test_targets,
    )
    from orchestrator.verifiers import run_pytest_targets

    ws = resolve_run_workspace(rows)
    patch_ctx = patch_context_from_run_rows(rows)
    targets = resolve_patch_test_targets((), patch_ctx)
    if not targets:
        targets = ["tests/"]
    existing = [t for t in targets if (ws / t).is_file() or (ws / t).is_dir()]
    if not existing:
        return {"tests_passed": True, "detail": "no mapped test targets; skipped", "exit_code": 0}
    code, out = run_pytest_targets(ws, existing, timeout_seconds=120.0)
    return {
        "tests_passed": code == 0,
        "exit_code": code,
        "detail": (out or "")[:4000],
        "targets": existing,
    }


@router.post(
    "/runs/{run_id}/maker/launch-eval",
    response_model=LaunchEvalResponse,
    response_model_exclude_none=True,
    responses={
        **llm_json_openapi_responses(not_found=PROBLEM_RESPONSE_404),  # sak499-c
        422: PROBLEM_RESPONSE_422,
    },
    summary="Launch eval scorecard (`sak482-f`)",
)
def post_maker_launch_eval(run_id: UUID, store: StoreDep) -> dict[str, Any]:
    rows = store.list_run_events(str(run_id))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(run_id)}),
        )
    from maker.workspace.workspace import resolve_run_workspace
    from orchestrator.launch.launch_eval_catalog import attach_context_from_run
    from orchestrator.launch.launch_evaluator import (
        emit_launch_eval_completed,
        evaluate_workspace_rubric,
    )

    ws = resolve_run_workspace(rows)
    if not ws.is_dir():
        raise HTTPException(
            status_code=422,
            detail=problem("workspace_not_found", "run has no attached workspace"),
        )
    from orchestrator.launch.launch_evaluator import merge_dev_env_into_scorecard

    attach = attach_context_from_run(rows)
    try:
        scorecard = evaluate_workspace_rubric(ws)
    except RuntimeError as exc:
        if "broker_miss" not in str(exc):
            raise
        from broker_client.dual_run_route import map_domain_broker_http_miss
        from broker_client.flags import broker_llm_enabled, broker_llm_only

        return map_domain_broker_http_miss(  # sak500-b
            exc,
            feature="launch_eval",
            enabled=broker_llm_enabled,
            only=broker_llm_only,
            only_code="broker_llm_unavailable",
            only_msg=(
                "Launch eval unavailable under NIMBUSWARE_BROKER_LLM=2; use SwissArmyNoife llm_chat"
            ),
        )
    scorecard = merge_dev_env_into_scorecard(scorecard, rows)
    emit_launch_eval_completed(store, run_id, scorecard, attach_context=attach or None)
    payload = scorecard.to_dict()
    if attach:
        payload["attach_context"] = attach
    return payload

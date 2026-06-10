from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from nimbusware_api.deps import StoreDep
from nimbusware_api.errors import problem
from nimbusware_api.schemas.openapi import PROBLEM_RESPONSE_404
from nimbusware_maker.workspace import resolve_run_workspace
from nimbusware_orchestrator.browser_controller import run_dev_env_ui_regression
from nimbusware_orchestrator.dev_env_observability import dev_env_theater_excerpt, tail_dev_env_logs
from nimbusware_orchestrator.dev_env_regression import run_dev_env_regression
from nimbusware_orchestrator.dev_env_supervisor import (
    dev_env_status,
    frontend_base_url,
    probe_dev_environment_health,
    start_dev_environment,
    stop_dev_environment,
)
from nimbusware_orchestrator.launch_flow_resolver import resolve_launch_flows
from nimbusware_orchestrator.ui_flow_dsl import DEFAULT_TINY_WEB_LOGIN_FLOW

router = APIRouter()


class DevEnvStatusResponse(BaseModel):
    run_id: str
    active: bool = False
    session: dict[str, Any] | None = None
    probe: dict[str, Any] = Field(default_factory=dict)
    logs: dict[str, Any] = Field(default_factory=dict)


class DevEnvActionResponse(BaseModel):
    ok: bool
    run_id: str
    session: dict[str, Any] | None = None
    error: str | None = None
    probe: dict[str, Any] = Field(default_factory=dict)


class DevEnvRegressionResponse(BaseModel):
    passed: bool
    detail: str = ""
    put_e2e: dict[str, Any] | None = None
    flow_id: str | None = None


class UiRegressionRequest(BaseModel):
    flow_id: str | None = None


@router.get(
    "/runs/{run_id}/dev-env/status",
    response_model=DevEnvStatusResponse,
    responses={404: PROBLEM_RESPONSE_404},
)
def get_dev_env_status(run_id: UUID, store: StoreDep) -> DevEnvStatusResponse:
    rows = store.list_run_events(str(run_id))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(run_id)}),
        )
    workspace = resolve_run_workspace(rows)
    status = dev_env_status(workspace)
    logs = tail_dev_env_logs(workspace)
    return DevEnvStatusResponse(
        run_id=str(run_id),
        active=bool(status.get("active")),
        session=status.get("session"),
        probe=status.get("probe") or {},
        logs=logs,
    )


@router.post(
    "/runs/{run_id}/dev-env/start",
    response_model=DevEnvActionResponse,
    responses={404: PROBLEM_RESPONSE_404},
)
def post_dev_env_start(run_id: UUID, store: StoreDep) -> DevEnvActionResponse:
    rows = store.list_run_events(str(run_id))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(run_id)}),
        )
    workspace = resolve_run_workspace(rows)
    result = start_dev_environment(store, run_id, workspace)
    return DevEnvActionResponse(
        ok=result.ok,
        run_id=str(run_id),
        session=result.session.to_dict() if result.session else None,
        error=result.error,
        probe=result.probe,
    )


@router.post(
    "/runs/{run_id}/dev-env/stop",
    response_model=DevEnvActionResponse,
    responses={404: PROBLEM_RESPONSE_404},
)
def post_dev_env_stop(run_id: UUID, store: StoreDep) -> DevEnvActionResponse:
    rows = store.list_run_events(str(run_id))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(run_id)}),
        )
    workspace = resolve_run_workspace(rows)
    stop_dev_environment(store, run_id, workspace)
    return DevEnvActionResponse(ok=True, run_id=str(run_id))


@router.post(
    "/runs/{run_id}/dev-env/regression",
    response_model=DevEnvRegressionResponse,
    responses={404: PROBLEM_RESPONSE_404},
)
def post_dev_env_regression(run_id: UUID, store: StoreDep) -> DevEnvRegressionResponse:
    rows = store.list_run_events(str(run_id))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(run_id)}),
        )
    workspace = resolve_run_workspace(rows)
    outcome = run_dev_env_regression(store, run_id, workspace)
    put_dict = outcome.put_e2e.to_dict() if outcome.put_e2e else None
    return DevEnvRegressionResponse(passed=outcome.passed, detail=outcome.detail, put_e2e=put_dict)


@router.post(
    "/runs/{run_id}/dev-env/ui-regression",
    response_model=DevEnvRegressionResponse,
    responses={404: PROBLEM_RESPONSE_404},
)
def post_dev_env_ui_regression(
    run_id: UUID,
    store: StoreDep,
    flow_id: str | None = Query(default=None),
    body: UiRegressionRequest | None = None,
) -> DevEnvRegressionResponse:
    rows = store.list_run_events(str(run_id))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(run_id)}),
        )
    workspace = resolve_run_workspace(rows)
    base = frontend_base_url(workspace)
    if not base:
        return DevEnvRegressionResponse(passed=False, detail="dev_env_not_running")
    override = flow_id or (body.flow_id if body else None)
    resolved = resolve_launch_flows(rows, workspace, ui_flow_id=override)
    flow = resolved.ui_flow or DEFAULT_TINY_WEB_LOGIN_FLOW
    ui_result = run_dev_env_ui_regression(
        store,
        run_id,
        base_url=base,
        flow=flow,
        workspace=workspace,
    )
    return DevEnvRegressionResponse(
        passed=ui_result.passed,
        detail=ui_result.detail,
        flow_id=flow.flow_id,
    )


@router.get(
    "/runs/{run_id}/dev-env/theater",
    responses={404: PROBLEM_RESPONSE_404},
)
def get_dev_env_theater(run_id: UUID, store: StoreDep) -> dict[str, Any]:
    rows = store.list_run_events(str(run_id))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(run_id)}),
        )
    workspace = resolve_run_workspace(rows)
    probe_dev_environment_health(store, run_id, workspace, emit_events=False)
    return dev_env_theater_excerpt(workspace)

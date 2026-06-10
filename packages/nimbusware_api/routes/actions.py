from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from agent_core.models import (
    EventType,
    GateOverriddenEvent,
    GateOverriddenPayload,
    RunEscalatedEvent,
    RunEscalatedPayload,
    StageStartedEvent,
    StageStartedPayload,
)
from nimbusware_api.admin import AdminDep
from nimbusware_api.deps import OrchDep, StoreDep
from nimbusware_api.errors import problem
from nimbusware_api.schemas.openapi import (
    PROBLEM_RESPONSE_401,
    PROBLEM_RESPONSE_404,
    PROBLEM_RESPONSE_422,
    PROBLEM_RESPONSE_500,
    PROBLEM_RESPONSE_503,
)
from nimbusware_orchestrator.role_execute import (
    resolve_taxonomy_key,
    supported_role_taxonomy_keys,
)

router = APIRouter(tags=["actions"])


class RoleExecuteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: UUID
    workspace_path: str | None = Field(default=None, max_length=512)


class EscalateBody(BaseModel):
    actor_id: str = Field(min_length=1)
    reason_code: str = Field(min_length=1)
    notes: str | None = None


class OverrideGateBody(BaseModel):
    actor_id: str = Field(min_length=1)
    reason_code: str = Field(min_length=1)
    stage_name: str = Field(min_length=1)
    policy_snapshot_id: str | None = None


@router.post(
    "/runs/{run_id}/actions/retry",
    responses={
        200: {
            "description": "Retry stage marker appended",
            "content": {
                "application/json": {"example": {"status": "retry_recorded"}},
            },
        },
        404: PROBLEM_RESPONSE_404,
        422: PROBLEM_RESPONSE_422,
        500: PROBLEM_RESPONSE_500,
    },
)
def retry_stage(run_id: UUID, store: StoreDep) -> dict[str, str]:
    rid_s = str(run_id)
    rows = store.list_run_events(rid_s)
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": rid_s}),
        )
    rid = run_id
    store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=uuid4(),
            run_id=rid,
            occurred_at=datetime.now(timezone.utc),
            payload=StageStartedPayload(stage_name="retry", attempt=1),
        ),
    )
    return {"status": "retry_recorded"}


@router.post(
    "/runs/{run_id}/actions/escalate",
    responses={
        200: {
            "description": "Escalation event appended",
            "content": {
                "application/json": {"example": {"status": "escalated"}},
            },
        },
        404: PROBLEM_RESPONSE_404,
        422: PROBLEM_RESPONSE_422,
        500: PROBLEM_RESPONSE_500,
    },
)
def escalate(run_id: UUID, body: EscalateBody, store: StoreDep) -> dict[str, str]:
    rid_s = str(run_id)
    rows = store.list_run_events(rid_s)
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": rid_s}),
        )
    rid = run_id
    store.append(
        RunEscalatedEvent(
            event_type=EventType.RUN_ESCALATED,
            event_id=uuid4(),
            run_id=rid,
            occurred_at=datetime.now(timezone.utc),
            payload=RunEscalatedPayload(
                actor_id=body.actor_id,
                reason_code=body.reason_code,
                notes=body.notes,
            ),
        ),
    )
    return {"status": "escalated"}


@router.post(
    "/runs/{run_id}/actions/override-gate",
    responses={
        200: {
            "description": "Gate override event appended (audit trail only)",
            "content": {
                "application/json": {"example": {"status": "gate_overridden"}},
            },
        },
        404: PROBLEM_RESPONSE_404,
        422: PROBLEM_RESPONSE_422,
        500: PROBLEM_RESPONSE_500,
    },
)
def override_gate(run_id: UUID, body: OverrideGateBody, store: StoreDep) -> dict[str, str]:
    rid_s = str(run_id)
    rows = store.list_run_events(rid_s)
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": rid_s}),
        )
    rid = run_id
    store.append(
        GateOverriddenEvent(
            event_type=EventType.GATE_OVERRIDDEN,
            event_id=uuid4(),
            run_id=rid,
            occurred_at=datetime.now(timezone.utc),
            payload=GateOverriddenPayload(
                actor_id=body.actor_id,
                reason_code=body.reason_code,
                stage_name=body.stage_name,
                policy_snapshot_id=body.policy_snapshot_id,
            ),
        ),
    )
    return {"status": "gate_overridden"}


@router.post(
    "/roles/{role_id}/execute",
    responses={
        200: {
            "description": "Role stage dispatched",
            "content": {
                "application/json": {
                    "example": {
                        "status": "executed",
                        "taxonomy_key": "planner",
                        "stage_name": "planner",
                        "run_id": "00000000-0000-4000-8000-000000000001",
                    },
                },
            },
        },
        401: PROBLEM_RESPONSE_401,
        404: PROBLEM_RESPONSE_404,
        422: PROBLEM_RESPONSE_422,
        500: PROBLEM_RESPONSE_500,
        503: PROBLEM_RESPONSE_503,
    },
)
def execute_role(
    role_id: str,
    body: RoleExecuteRequest,
    _admin: AdminDep,
    orch: OrchDep,
    store: StoreDep,
) -> dict[str, Any]:
    rows = store.list_run_events(str(body.run_id))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(body.run_id)}),
        )
    try:
        resolve_taxonomy_key(orch._registry, role_id)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=problem("role_not_found", f"unknown role: {role_id}"),
        ) from None
    ws = Path(body.workspace_path).resolve() if body.workspace_path else None
    try:
        from typing import Any, cast

        host: Any = orch
        return cast(
            dict[str, Any],
            host.execute_role_for_run(body.run_id, role_id, workspace=ws),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=problem(
                "role_execute_unsupported",
                str(exc),
                details={"supported_roles": supported_role_taxonomy_keys(orch._registry)},
            ),
        ) from exc

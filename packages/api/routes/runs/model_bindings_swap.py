from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from api.deps import StoreDep
from api.errors import problem
from api.user import UserDep, maker_user_id_str
from orchestrator.model_binding_audit import (
    RoleClaimConflictError,
    assert_role_claim_available,
    extract_model_binding_audit_rows,
)
from orchestrator.model_binding_swap import (
    append_model_binding_override,
    append_role_claim,
    append_role_release,
)

router = APIRouter(tags=["runs"])


class ModelBindingSwapBody(BaseModel):
    agent_role: str = Field(min_length=1, max_length=120)
    provider_id: str = Field(min_length=1, max_length=80)
    provider_kind: str = Field(default="local", pattern="^(local|cloud)$")
    model_id: str = Field(min_length=1, max_length=200)


class RoleClaimBody(BaseModel):
    agent_role: str = Field(min_length=1, max_length=120)
    provider_id: str = Field(min_length=1, max_length=80)
    model_id: str = Field(min_length=1, max_length=200)


def _require_run(store: StoreDep, run_id: UUID) -> None:
    if not store.list_run_events(str(run_id)):
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(run_id)}),
        )


@router.post("/runs/{run_id}/model-bindings/swap")
def post_run_model_binding_swap(
    run_id: UUID,
    body: ModelBindingSwapBody,
    store: StoreDep,
    _: UserDep,
) -> dict[str, Any]:
    _require_run(store, run_id)
    payload = append_model_binding_override(
        store,
        run_id,
        agent_role=body.agent_role,
        provider_id=body.provider_id,
        provider_kind=body.provider_kind,
        model_id=body.model_id,
    )
    return {"ok": True, "event": "model.binding.overridden", "payload": payload}


@router.post("/runs/{run_id}/role-claims")
def post_run_role_claim(
    run_id: UUID,
    body: RoleClaimBody,
    store: StoreDep,
    request: Request,
    _: UserDep,
) -> dict[str, Any]:
    _require_run(store, run_id)
    rows = store.list_run_events(str(run_id))
    claimer = maker_user_id_str(request)
    try:
        assert_role_claim_available(
            rows,
            agent_role=body.agent_role,
            claimer_user_id=claimer,
        )
    except RoleClaimConflictError as exc:
        raise HTTPException(
            status_code=409,
            detail=problem(
                "role_claim_conflict",
                f"Role {body.agent_role} is already claimed",
                details={"existing_claimer": exc.existing_claimer},
            ),
        ) from exc
    payload = append_role_claim(
        store,
        run_id,
        agent_role=body.agent_role,
        provider_id=body.provider_id,
        model_id=body.model_id,
        claimer_user_id=claimer,
    )
    return {"ok": True, "event": "workload.role_claimed", "payload": payload}


@router.delete("/runs/{run_id}/role-claims/{agent_role}")
def delete_run_role_claim(
    run_id: UUID,
    agent_role: str,
    store: StoreDep,
    _: UserDep,
) -> dict[str, Any]:
    _require_run(store, run_id)
    payload = append_role_release(store, run_id, agent_role=agent_role)
    return {"ok": True, "event": "workload.role_released", "payload": payload}


@router.get("/runs/{run_id}/model-bindings/audit")
def get_run_model_binding_audit(
    run_id: UUID,
    store: StoreDep,
    _: UserDep,
) -> dict[str, Any]:
    rows = store.list_run_events(str(run_id))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(run_id)}),
        )
    events = extract_model_binding_audit_rows(rows)
    return {"run_id": str(run_id), "events": events, "count": len(events)}

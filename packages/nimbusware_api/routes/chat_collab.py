from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from nimbusware_api.deps import ChatStoreDep, StoreDep
from nimbusware_api.errors import problem
from nimbusware_api.routes.chat_common import (
    ChatMessageResponse,
    session_or_404,
)
from nimbusware_api.schemas.openapi import PROBLEM_RESPONSE_404, PROBLEM_RESPONSE_422
from nimbusware_api.user import UserDep, maker_user_id_str
from nimbusware_orchestrator.model_binding_audit import (
    RoleClaimConflictError,
    assert_role_claim_available,
)
from nimbusware_orchestrator.model_binding_swap import (
    append_model_binding_override,
    append_role_claim,
    append_role_release,
)

router = APIRouter(prefix="/chat", tags=["maker"])


class SessionModelBindingSwapBody(BaseModel):
    run_id: UUID
    agent_role: str = Field(min_length=1, max_length=120)
    provider_id: str = Field(min_length=1, max_length=80)
    provider_kind: str = Field(default="local", pattern="^(local|cloud)$")
    model_id: str = Field(min_length=1, max_length=200)


@router.post(
    "/sessions/{session_id}/model-bindings/swap",
    response_model=ChatMessageResponse,
    responses={404: PROBLEM_RESPONSE_404, 422: PROBLEM_RESPONSE_422},
)
def session_model_binding_swap(
    session_id: UUID,
    body: SessionModelBindingSwapBody,
    chat_store: ChatStoreDep,
    store: StoreDep,
    _user: UserDep,
) -> ChatMessageResponse:
    session_or_404(chat_store, session_id)
    if not store.list_run_events(str(body.run_id)):
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(body.run_id)}),
        )
    payload = append_model_binding_override(
        store,
        body.run_id,
        agent_role=body.agent_role,
        provider_id=body.provider_id,
        provider_kind=body.provider_kind,
        model_id=body.model_id,
    )
    label = f"{body.agent_role} â†’ {body.model_id} ({body.provider_id})"
    turn = chat_store.append_turn(
        session_id,
        role="system",
        text=f"Model swap: {label}",
        payload={"model_swap": payload},
    )
    message = {
        "role": "system",
        "text": turn.text,
        "turn_id": str(turn.turn_id),
        "posted_at": turn.posted_at.isoformat() if turn.posted_at else None,
        "model_swap": payload,
    }
    return ChatMessageResponse(
        message=message,
        classification={"work_type": "system", "rationale": "model_swap"},
        turn=turn.to_dict(),
    )


class SessionRoleClaimBody(BaseModel):
    run_id: UUID
    agent_role: str = Field(min_length=1, max_length=120)
    provider_id: str = Field(min_length=1, max_length=80)
    model_id: str = Field(min_length=1, max_length=200)


@router.post("/sessions/{session_id}/role-claims")
def session_role_claim(
    session_id: UUID,
    body: SessionRoleClaimBody,
    chat_store: ChatStoreDep,
    store: StoreDep,
    request: Request,
    _user: UserDep,
) -> dict[str, Any]:
    session_or_404(chat_store, session_id)
    if not store.list_run_events(str(body.run_id)):
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(body.run_id)}),
        )
    rows = store.list_run_events(str(body.run_id))
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
        body.run_id,
        agent_role=body.agent_role,
        provider_id=body.provider_id,
        model_id=body.model_id,
        claimer_user_id=claimer,
    )
    chat_store.append_turn(
        session_id,
        role="system",
        text=f"Role claimed: {body.agent_role} â†’ {body.model_id}",
        payload={"role_claim": payload},
    )
    return {"ok": True, "event": "workload.role_claimed", "payload": payload}


@router.delete("/sessions/{session_id}/role-claims/{agent_role}")
def session_role_release(
    session_id: UUID,
    agent_role: str,
    chat_store: ChatStoreDep,
    store: StoreDep,
    _user: UserDep,
    run_id: Annotated[UUID | None, Query()] = None,
) -> dict[str, Any]:
    session_or_404(chat_store, session_id)
    resolved_run_id = run_id
    if resolved_run_id is None:
        sess = chat_store.get_session(session_id)
        if sess is None:
            raise HTTPException(
                status_code=404,
                detail=problem("session_not_found", "session not found"),
            )
        resolved_run_id = sess.run_id
    if resolved_run_id is None or not store.list_run_events(str(resolved_run_id)):
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found"),
        )
    payload = append_role_release(store, resolved_run_id, agent_role=agent_role)
    chat_store.append_turn(
        session_id,
        role="system",
        text=f"Role released: {agent_role}",
        payload={"role_release": payload},
    )
    return {"ok": True, "event": "workload.role_released", "payload": payload}



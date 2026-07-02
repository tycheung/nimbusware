from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from nimbusware_api.deps import ChatStoreDep, CollabStoreDep, HostTransferStoreDep, StoreDep
from nimbusware_api.errors import problem
from nimbusware_api.routes.auth import AuthUserDep
from nimbusware_api.routes.chat_common import (
    ChatMessageResponse,
    require_collab_enabled,
    session_or_404,
)
from nimbusware_api.schemas.openapi import PROBLEM_RESPONSE_404, PROBLEM_RESPONSE_422
from nimbusware_api.user import UserDep, maker_user_id_str
from nimbusware_auth.permissions import require_session_participant
from nimbusware_maker.host_transfer_bundle import build_transfer_manifest, import_transfer_bundle
from nimbusware_maker.host_transfer_store import default_consent_hours
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


class HostTransferBody(BaseModel):
    to_user_id: UUID


class ImportBundleBody(BaseModel):
    manifest: dict[str, Any]


@router.post("/sessions/{session_id}/host-transfer")
def request_host_transfer(
    session_id: UUID,
    body: HostTransferBody,
    chat_store: ChatStoreDep,
    collab_store: CollabStoreDep,
    transfer_store: HostTransferStoreDep,
    user: AuthUserDep,
) -> dict[str, Any]:
    require_collab_enabled()
    sess = session_or_404(chat_store, session_id)
    require_session_participant(
        collab_store,
        session_id=session_id,
        user_id=user.user_id,
        minimum_role="session_admin",
    )
    from_host = sess.host_user_id or user.user_id
    row = transfer_store.create(
        session_id=session_id,
        project_id=sess.project_id,
        from_host_user_id=from_host,
        to_user_id=body.to_user_id,
        initiated_by_user_id=user.user_id,
        consent_hours=default_consent_hours(),
    )
    chat_store.append_turn(
        session_id,
        role="system",
        text=f"Host transfer requested -> {body.to_user_id}",
        payload={"host_transfer": row.to_dict()},
    )
    return {"ok": True, "transfer": row.to_dict()}


@router.get("/sessions/{session_id}/host-transfer")
def list_host_transfers(
    session_id: UUID,
    chat_store: ChatStoreDep,
    transfer_store: HostTransferStoreDep,
    _: AuthUserDep,
) -> dict[str, Any]:
    require_collab_enabled()
    session_or_404(chat_store, session_id)
    rows = transfer_store.list_for_session(session_id)
    return {"transfers": [r.to_dict() for r in rows]}


@router.get("/sessions/{session_id}/host-transfer/{transfer_id}/bundle")
def export_host_transfer_bundle(
    session_id: UUID,
    transfer_id: UUID,
    chat_store: ChatStoreDep,
    transfer_store: HostTransferStoreDep,
    user: AuthUserDep,
) -> dict[str, Any]:
    require_collab_enabled()
    session_or_404(chat_store, session_id)
    row = transfer_store.get(transfer_id)
    if row is None or row.session_id != session_id:
        raise HTTPException(
            status_code=404,
            detail=problem("transfer_not_found", "host transfer not found"),
        )
    if row.status not in {"frozen", "transferring", "completed"}:
        raise HTTPException(
            status_code=409,
            detail=problem("transfer_not_ready", "transfer must be accepted before export"),
        )
    manifest = build_transfer_manifest(
        chat_store,
        session_id=session_id,
        transfer_id=transfer_id,
    )
    return {"manifest": manifest}


@router.post("/sessions/{session_id}/host-transfer/{transfer_id}/accept")
def accept_host_transfer(
    session_id: UUID,
    transfer_id: UUID,
    chat_store: ChatStoreDep,
    transfer_store: HostTransferStoreDep,
    user: AuthUserDep,
) -> dict[str, Any]:
    require_collab_enabled()
    session_or_404(chat_store, session_id)
    row = transfer_store.get(transfer_id)
    if row is None or row.session_id != session_id:
        raise HTTPException(
            status_code=404,
            detail=problem("transfer_not_found", "host transfer not found"),
        )
    if row.to_user_id != user.user_id:
        raise HTTPException(
            status_code=403,
            detail=problem("forbidden", "only the nominated user may accept"),
        )
    manifest = build_transfer_manifest(
        chat_store,
        session_id=session_id,
        transfer_id=transfer_id,
    )
    frozen = transfer_store.accept_and_freeze(transfer_id, manifest=manifest)
    session = chat_store.get_session(session_id)
    if session is None:
        raise HTTPException(
            status_code=404,
            detail=problem("session_not_found", "chat session not found"),
        )
    meta = dict(session.metadata or {})
    meta["transfer_frozen"] = True
    chat_store.update_session(session_id, metadata=meta)
    chat_store.append_turn(
        session_id,
        role="system",
        text="Host transfer accepted; session frozen for cutover",
        payload={"host_transfer_frozen": frozen.to_dict()},
    )
    return {"ok": True, "transfer": frozen.to_dict()}


@router.post("/sessions/{session_id}/host-transfer/{transfer_id}/import")
def import_host_transfer_bundle(
    session_id: UUID,
    transfer_id: UUID,
    body: ImportBundleBody,
    chat_store: ChatStoreDep,
    transfer_store: HostTransferStoreDep,
    user: AuthUserDep,
) -> dict[str, Any]:
    require_collab_enabled()
    row = transfer_store.get(transfer_id)
    if row is None or row.session_id != session_id:
        raise HTTPException(
            status_code=404,
            detail=problem("transfer_not_found", "host transfer not found"),
        )
    if row.to_user_id != user.user_id:
        raise HTTPException(
            status_code=403,
            detail=problem("forbidden", "only the nominated user may import"),
        )
    import_transfer_bundle(chat_store, body.manifest)
    completed = transfer_store.complete(transfer_id, new_host_user_id=user.user_id)
    chat_store.update_session(session_id, host_user_id=user.user_id)
    session = chat_store.get_session(session_id)
    if session is None:
        raise HTTPException(
            status_code=404,
            detail=problem("session_not_found", "chat session not found"),
        )
    meta = dict(session.metadata or {})
    meta.pop("transfer_frozen", None)
    chat_store.update_session(session_id, metadata=meta)
    chat_store.append_turn(
        session_id,
        role="system",
        text=f"Host transfer completed; {user.user_id} is canonical host",
        payload={"host_transfer_completed": completed.to_dict()},
    )
    return {"ok": True, "transfer": completed.to_dict()}


@router.post("/sessions/{session_id}/host-transfer/{transfer_id}/complete")
def complete_host_transfer(
    session_id: UUID,
    transfer_id: UUID,
    chat_store: ChatStoreDep,
    transfer_store: HostTransferStoreDep,
    user: AuthUserDep,
) -> dict[str, Any]:
    require_collab_enabled()
    session_or_404(chat_store, session_id)
    row = transfer_store.get(transfer_id)
    if row is None or row.session_id != session_id:
        raise HTTPException(
            status_code=404,
            detail=problem("transfer_not_found", "host transfer not found"),
        )
    if row.status != "frozen":
        raise HTTPException(
            status_code=409,
            detail=problem("transfer_not_frozen", "transfer must be frozen"),
        )
    completed = transfer_store.complete(transfer_id, new_host_user_id=row.to_user_id)
    chat_store.update_session(session_id, host_user_id=row.to_user_id)
    session = chat_store.get_session(session_id)
    if session is None:
        raise HTTPException(
            status_code=404,
            detail=problem("session_not_found", "chat session not found"),
        )
    meta = dict(session.metadata or {})
    meta.pop("transfer_frozen", None)
    chat_store.update_session(session_id, metadata=meta)
    return {"ok": True, "transfer": completed.to_dict()}


@router.post("/sessions/{session_id}/host-transfer/{transfer_id}/decline")
def decline_host_transfer(
    session_id: UUID,
    transfer_id: UUID,
    chat_store: ChatStoreDep,
    transfer_store: HostTransferStoreDep,
    user: AuthUserDep,
) -> dict[str, Any]:
    require_collab_enabled()
    session_or_404(chat_store, session_id)
    row = transfer_store.get(transfer_id)
    if row is None or row.session_id != session_id:
        raise HTTPException(
            status_code=404,
            detail=problem("transfer_not_found", "host transfer not found"),
        )
    if row.to_user_id != user.user_id:
        raise HTTPException(
            status_code=403,
            detail=problem("forbidden", "only the nominated user may decline"),
        )
    if row.status != "pending":
        raise HTTPException(
            status_code=409,
            detail=problem("transfer_not_pending", "transfer is not pending"),
        )
    declined = transfer_store.decline(transfer_id)
    chat_store.append_turn(
        session_id,
        role="system",
        text="Host transfer declined",
        payload={"host_transfer_declined": declined.to_dict()},
    )
    return {"ok": True, "transfer": declined.to_dict()}

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from nimbusware_api.deps import ChatStoreDep, CollabStoreDep
from nimbusware_api.errors import problem
from nimbusware_api.routes.auth import AuthUserDep
from nimbusware_api.routes.chat_collab_common import require_collab_enabled
from nimbusware_api.routes.chat_handlers import session_or_404 as _session_or_404
from nimbusware_auth.permissions import require_session_participant
from nimbusware_maker.host_transfer_store import default_consent_hours, host_transfer_store

router = APIRouter(prefix="/chat", tags=["maker"])


class HostTransferBody(BaseModel):
    to_user_id: UUID


@router.post("/sessions/{session_id}/host-transfer")
def request_host_transfer(
    session_id: UUID,
    body: HostTransferBody,
    chat_store: ChatStoreDep,
    collab_store: CollabStoreDep,
    user: AuthUserDep,
) -> dict[str, Any]:
    require_collab_enabled()
    sess = _session_or_404(chat_store, session_id)
    require_session_participant(
        collab_store,
        session_id=session_id,
        user_id=user.user_id,
        minimum_role="session_admin",
    )
    from_host = sess.host_user_id or user.user_id
    row = host_transfer_store().create(
        session_id=session_id,
        from_host_user_id=from_host,
        to_user_id=body.to_user_id,
        consent_hours=default_consent_hours(),
    )
    chat_store.append_turn(
        session_id,
        role="system",
        text=f"Host transfer requested → {body.to_user_id}",
        payload={"host_transfer": row.to_dict()},
    )
    return {"ok": True, "transfer": row.to_dict()}


@router.get("/sessions/{session_id}/host-transfer")
def list_host_transfers(
    session_id: UUID,
    chat_store: ChatStoreDep,
    _: AuthUserDep,
) -> dict[str, Any]:
    require_collab_enabled()
    _session_or_404(chat_store, session_id)
    rows = host_transfer_store().list_for_session(session_id)
    return {"transfers": [r.to_dict() for r in rows]}


@router.post("/sessions/{session_id}/host-transfer/{transfer_id}/accept")
def accept_host_transfer(
    session_id: UUID,
    transfer_id: UUID,
    chat_store: ChatStoreDep,
    user: AuthUserDep,
) -> dict[str, Any]:
    require_collab_enabled()
    _session_or_404(chat_store, session_id)
    row = host_transfer_store().get(transfer_id)
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
    row.status = "accepted"
    chat_store.update_session(session_id, host_user_id=user.user_id)
    chat_store.append_turn(
        session_id,
        role="system",
        text=f"Host transfer accepted by {user.user_id}",
        payload={"host_transfer_completed": row.to_dict()},
    )
    return {"ok": True, "transfer": row.to_dict()}

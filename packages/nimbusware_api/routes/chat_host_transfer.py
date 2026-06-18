from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from nimbusware_api.deps import ChatStoreDep, CollabStoreDep, HostTransferStoreDep
from nimbusware_api.errors import problem
from nimbusware_api.routes.auth import AuthUserDep
from nimbusware_api.routes.chat_collab_common import require_collab_enabled
from nimbusware_api.routes.chat_handlers import session_or_404 as _session_or_404
from nimbusware_auth.permissions import require_session_participant
from nimbusware_maker.host_transfer_bundle import build_transfer_manifest, import_transfer_bundle
from nimbusware_maker.host_transfer_store import default_consent_hours

router = APIRouter(prefix="/chat", tags=["maker"])


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
    sess = _session_or_404(chat_store, session_id)
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
        text=f"Host transfer requested → {body.to_user_id}",
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
    _session_or_404(chat_store, session_id)
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
    _session_or_404(chat_store, session_id)
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
    _session_or_404(chat_store, session_id)
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
    meta = dict(chat_store.get_session(session_id).metadata or {})
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
    meta = dict(chat_store.get_session(session_id).metadata or {})
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
    _session_or_404(chat_store, session_id)
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
    meta = dict(chat_store.get_session(session_id).metadata or {})
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
    _session_or_404(chat_store, session_id)
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

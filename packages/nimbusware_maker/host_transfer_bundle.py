from __future__ import annotations

import hashlib
import json
from typing import Any
from uuid import UUID

from nimbusware_maker.chat_store import ChatStore


def build_transfer_manifest(
    chat_store: ChatStore,
    *,
    session_id: UUID,
    transfer_id: UUID,
) -> dict[str, Any]:
    session = chat_store.get_session(session_id)
    if session is None:
        raise KeyError("chat_session_not_found")
    turns = chat_store.list_turns(session_id)
    payload = {
        "version": 1,
        "transfer_id": str(transfer_id),
        "session": session.to_dict(),
        "turns": [t.to_dict() for t in turns],
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    return {**payload, "checksum_sha256": digest}


def import_transfer_bundle(chat_store: ChatStore, manifest: dict[str, Any]) -> UUID:
    session_blob = manifest.get("session")
    if not isinstance(session_blob, dict):
        raise ValueError("invalid_manifest")
    session_id = UUID(str(session_blob["session_id"]))
    if chat_store.get_session(session_id) is None:
        raise KeyError("chat_session_not_found")
    host_id = session_blob.get("host_user_id")
    kw: dict[str, Any] = {}
    if host_id:
        kw["host_user_id"] = UUID(str(host_id))
    meta = dict(session_blob.get("metadata") or {})
    folder_raw = session_blob.get("folder_id")
    tags = session_blob.get("tags") or []
    if folder_raw:
        kw["folder_id"] = UUID(str(folder_raw))
    if tags:
        kw["tags"] = [str(t) for t in tags]
    if meta:
        kw["metadata"] = meta
    if kw:
        chat_store.update_session(session_id, **kw)
    return session_id

from __future__ import annotations

from contextvars import ContextVar
from uuid import UUID

_active_run_id: ContextVar[UUID | None] = ContextVar("host_collab_active_run_id", default=None)


def set_active_run_for_mesh(run_id: UUID | None) -> None:
    _active_run_id.set(run_id)


def active_run_for_mesh() -> UUID | None:
    return _active_run_id.get()


def hydrate_mesh_binding_from_run(run_id: UUID, *, actor_user_id: str = "") -> bool:
    from orchestrator.collab.binding_resolver import participant_binding_overrides
    from orchestrator.collab.mesh_context import (
        mesh_actor_user_id,
        mesh_participant_overrides,
        set_mesh_binding_context,
    )

    if mesh_participant_overrides() is not None:
        return False
    try:
        from env.env_flags import nimbusware_database_url
        from maker.chat.session_store import build_chat_store

        chat_store = build_chat_store(nimbusware_database_url())
        sess = chat_store.find_session_by_run_id(run_id)
        if sess is None:
            return False
        meta = sess.metadata if isinstance(sess.metadata, dict) else {}
        actor = actor_user_id.strip() or mesh_actor_user_id().strip()
        if not actor:
            collab = meta.get("collab") if isinstance(meta.get("collab"), dict) else {}
            actor = str(collab.get("host_user_id") or meta.get("host_user_id") or "").strip()
        overrides = participant_binding_overrides(meta, actor) if actor else {}
        if not overrides and not actor:
            return False
        set_mesh_binding_context(participant_overrides=overrides or None, actor_user_id=actor)
        return True
    except Exception:
        return False


def ensure_mesh_binding_for_llm() -> None:
    from orchestrator.collab.mesh_context import mesh_participant_overrides

    if mesh_participant_overrides() is not None:
        return
    run_id = active_run_for_mesh()
    if run_id is not None:
        hydrate_mesh_binding_from_run(run_id)

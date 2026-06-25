from __future__ import annotations

from contextvars import ContextVar
from typing import Any

_participant_overrides: ContextVar[dict[str, Any] | None] = ContextVar(
    "collab_mesh_participant_overrides",
    default=None,
)
_actor_user_id: ContextVar[str] = ContextVar("collab_mesh_actor_user_id", default="")


def set_mesh_binding_context(
    *,
    participant_overrides: dict[str, Any] | None,
    actor_user_id: str = "",
) -> None:
    _participant_overrides.set(participant_overrides)
    _actor_user_id.set(actor_user_id)


def clear_mesh_binding_context() -> None:
    _participant_overrides.set(None)
    _actor_user_id.set("")


def mesh_participant_overrides() -> dict[str, Any] | None:
    return _participant_overrides.get()


def mesh_actor_user_id() -> str:
    return _actor_user_id.get()

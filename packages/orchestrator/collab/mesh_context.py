from __future__ import annotations

from contextvars import ContextVar
from typing import Any

_participant_overrides: ContextVar[dict[str, Any] | None] = ContextVar(
    "collab_mesh_participant_overrides",
    default=None,
)
_actor_user_id: ContextVar[str] = ContextVar("collab_mesh_actor_user_id", default="")
_agent_overlay_prompt: ContextVar[str] = ContextVar("collab_mesh_agent_overlay_prompt", default="")


def set_mesh_binding_context(
    *,
    participant_overrides: dict[str, Any] | None,
    actor_user_id: str = "",
    agent_overlay_prompt: str = "",
) -> None:
    _participant_overrides.set(participant_overrides)
    _actor_user_id.set(actor_user_id)
    _agent_overlay_prompt.set(agent_overlay_prompt.strip())


def clear_mesh_binding_context() -> None:
    _participant_overrides.set(None)
    _actor_user_id.set("")
    _agent_overlay_prompt.set("")


def mesh_participant_overrides() -> dict[str, Any] | None:
    return _participant_overrides.get()


def mesh_actor_user_id() -> str:
    return _actor_user_id.get()


def mesh_agent_overlay_prompt() -> str:
    return _agent_overlay_prompt.get()

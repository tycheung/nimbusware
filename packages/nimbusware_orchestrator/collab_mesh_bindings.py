from __future__ import annotations

from typing import Any

from agent_core.mapping import mapping_or_empty
from nimbusware_orchestrator.collab_binding_resolver import participant_binding_overrides


def executor_binding_hint(
    session_metadata: dict[str, Any] | None,
    *,
    executor_user_id: str,
    agent_role: str,
) -> dict[str, str] | None:
    if not executor_user_id:
        return None
    overrides = participant_binding_overrides(session_metadata, executor_user_id)
    block = mapping_or_empty(overrides.get(agent_role))
    if not block:
        return None
    return {
        "provider_kind": str(block.get("provider_kind") or "local"),
        "provider_id": str(block.get("provider_id") or "ollama"),
        "model_id": str(block.get("model_id") or ""),
        "connection_id": str(block.get("connection_id") or ""),
    }


def participant_overrides_from_hint(hint: dict[str, Any] | None, agent_role: str) -> dict[str, Any]:
    if not hint or not agent_role:
        return {}
    return {agent_role: dict(hint)}

from __future__ import annotations

from typing import Any

from agent_core.mapping import mapping_or_empty


def participant_binding_overrides(
    session_metadata: dict[str, Any] | None, user_id: str
) -> dict[str, Any]:
    if not session_metadata or not user_id:
        return {}
    collab = mapping_or_empty(session_metadata.get("collab"))
    by_user = mapping_or_empty(collab.get("participant_bindings"))
    return mapping_or_empty(by_user.get(user_id))


def merge_participant_binding(
    session_metadata: dict[str, Any] | None,
    *,
    user_id: str,
    agent_role: str,
    binding: dict[str, Any],
) -> dict[str, Any]:
    meta = dict(session_metadata or {})
    collab = dict(mapping_or_empty(meta.get("collab")))
    by_user = dict(mapping_or_empty(collab.get("participant_bindings")))
    roles = dict(mapping_or_empty(by_user.get(user_id)))
    roles[agent_role] = binding
    by_user[user_id] = roles
    collab["participant_bindings"] = by_user
    meta["collab"] = collab
    return meta


def participant_memory_policy(
    session_metadata: dict[str, Any] | None, user_id: str
) -> dict[str, bool]:
    if not session_metadata or not user_id:
        from nimbusware_memory.user_scope import memory_retrieval_policy

        return memory_retrieval_policy()
    collab = mapping_or_empty(session_metadata.get("collab"))
    by_user = mapping_or_empty(collab.get("memory_policy"))
    raw = by_user.get(user_id)
    if isinstance(raw, dict):
        return {
            "private": bool(raw.get("private", True)),
            "project_shared": bool(raw.get("project_shared", True)),
        }
    from nimbusware_memory.user_scope import memory_retrieval_policy

    return memory_retrieval_policy()


def merge_participant_memory_policy(
    session_metadata: dict[str, Any] | None,
    *,
    user_id: str,
    policy: dict[str, bool],
) -> dict[str, Any]:
    meta = dict(session_metadata or {})
    collab = dict(mapping_or_empty(meta.get("collab")))
    by_user = dict(mapping_or_empty(collab.get("memory_policy")))
    by_user[user_id] = {
        "private": bool(policy.get("private", True)),
        "project_shared": bool(policy.get("project_shared", True)),
    }
    collab["memory_policy"] = by_user
    meta["collab"] = collab
    return meta

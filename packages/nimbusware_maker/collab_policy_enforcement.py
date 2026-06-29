from __future__ import annotations

from typing import Any
from uuid import UUID

from nimbusware_config.collab_policy_store import load_collab_policy
from nimbusware_config.tenant_policy_store import load_tenant_collab_policy
from nimbusware_env import find_repo_root


class CollabPolicyViolation(ValueError):
    pass


def effective_collab_policy(tenant_slug: str | None) -> dict[str, Any]:
    slug = str(tenant_slug or "").strip()
    if slug:
        doc = load_tenant_collab_policy(slug)
    else:
        doc = load_collab_policy(find_repo_root())
    defaults = load_collab_policy(find_repo_root())
    return {**defaults, **doc}


def max_session_participants(tenant_slug: str | None) -> int:
    raw = effective_collab_policy(tenant_slug).get("max_session_participants")
    cap = 20
    if raw is not None:
        try:
            cap = int(raw)
        except (TypeError, ValueError):
            cap = 20
    return max(1, min(cap, 500))


def external_collaborators_allowed(tenant_slug: str | None) -> bool:
    return bool(effective_collab_policy(tenant_slug).get("allow_external_collaborators"))


def _participant_count(collab_store: Any, session_id: UUID) -> int:
    return len(collab_store.list_participants(session_id))


def _is_participant(collab_store: Any, session_id: UUID, user_id: UUID) -> bool:
    for row in collab_store.list_participants(session_id):
        if getattr(row, "user_id", None) == user_id:
            return True
    return False


def assert_participant_capacity(
    collab_store: Any,
    session_id: UUID,
    *,
    tenant_slug: str | None,
    user_id: UUID | None = None,
) -> None:
    if user_id is not None and _is_participant(collab_store, session_id, user_id):
        return
    cap = max_session_participants(tenant_slug)
    if _participant_count(collab_store, session_id) >= cap:
        msg = f"session participant limit ({cap}) reached"
        raise CollabPolicyViolation(msg)


def assert_link_join_allowed(*, tenant_slug: str | None) -> None:
    from nimbusware_env.env_flags import env_str

    bundle = env_str("NIMBUSWARE_SETUP_BUNDLE").strip() or "default"
    if bundle != "enterprise":
        return
    if external_collaborators_allowed(tenant_slug):
        return
    msg = "external collaborators disabled by tenant collab policy"
    raise CollabPolicyViolation(msg)

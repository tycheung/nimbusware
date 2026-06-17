from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, Request

from nimbusware_api.errors import problem
from nimbusware_auth.models import role_at_least
from nimbusware_auth.session_cookie import user_id_from_request
from nimbusware_auth.store import CollabStore
from nimbusware_env.env_flags import nimbusware_collab_enabled


def resolve_actor_user_id(request: Request) -> UUID | None:
    return user_id_from_request(request)


def require_session_participant(
    collab_store: CollabStore,
    *,
    session_id: UUID,
    user_id: UUID,
    minimum_role: str = "session_read",
) -> str:
    participant = collab_store.get_participant(session_id, user_id)
    if participant is None:
        raise HTTPException(
            status_code=403,
            detail=problem(
                "forbidden",
                "not a session participant",
                details={"session_id": str(session_id)},
            ),
        )
    if not role_at_least(participant.role, minimum_role):
        raise HTTPException(
            status_code=403,
            detail=problem(
                "forbidden",
                f"requires {minimum_role} or higher",
                details={"role": participant.role, "required": minimum_role},
            ),
        )
    return participant.role


def enforce_collab_turn_write(
    collab_store: CollabStore,
    *,
    session_id: UUID,
    user_id: UUID | None,
    collab_enabled: bool,
) -> None:
    if not collab_enabled:
        return
    if user_id is None:
        raise HTTPException(
            status_code=401,
            detail=problem("unauthorized", "sign in required for collaborative chat"),
        )
    require_session_participant(
        collab_store,
        session_id=session_id,
        user_id=user_id,
        minimum_role="session_write",
    )


def collab_active() -> bool:
    return nimbusware_collab_enabled()

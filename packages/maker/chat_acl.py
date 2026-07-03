from __future__ import annotations

from auth.models import ROLE_RANK


def max_participant_role(*roles: str | None) -> str | None:
    best: str | None = None
    best_rank = -1
    for role in roles:
        if not role:
            continue
        rank = ROLE_RANK.get(role, -1)
        if rank > best_rank:
            best_rank = rank
            best = role
    return best


def effective_session_role(
    *,
    direct_role: str | None,
    session_grant_roles: list[str],
    folder_grant_roles: list[str],
    tag_grant_roles: list[str],
) -> str | None:
    return max_participant_role(
        direct_role,
        *session_grant_roles,
        *folder_grant_roles,
        *tag_grant_roles,
    )

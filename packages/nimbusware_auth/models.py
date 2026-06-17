from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

SESSION_PARTICIPANT_ROLES = frozenset({"session_read", "session_write", "session_admin"})

ROLE_RANK = {
    "session_read": 0,
    "session_write": 1,
    "session_admin": 2,
}


def role_at_least(role: str, minimum: str) -> bool:
    return ROLE_RANK.get(role, -1) >= ROLE_RANK.get(minimum, 99)


@dataclass(frozen=True)
class UserRecord:
    user_id: UUID
    username: str
    display_name: str
    password_hash: str
    created_at: datetime
    is_owner: bool = False

    def to_public_dict(self) -> dict[str, str | bool]:
        return {
            "user_id": str(self.user_id),
            "username": self.username,
            "display_name": self.display_name,
            "is_owner": self.is_owner,
            "created_at": self.created_at.isoformat(),
        }


@dataclass(frozen=True)
class ParticipantRecord:
    session_id: UUID
    user_id: UUID
    role: str
    joined_at: datetime
    username: str | None = None
    display_name: str | None = None

    def to_dict(self) -> dict[str, str]:
        out = {
            "session_id": str(self.session_id),
            "user_id": str(self.user_id),
            "role": self.role,
            "joined_at": self.joined_at.isoformat(),
        }
        if self.username is not None:
            out["username"] = self.username
        if self.display_name is not None:
            out["display_name"] = self.display_name
        return out


@dataclass(frozen=True)
class InviteRecord:
    invite_id: UUID
    session_id: UUID
    role: str
    token: str
    expires_at: datetime
    created_by: UUID
    created_at: datetime

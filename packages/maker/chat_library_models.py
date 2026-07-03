from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

GRANTEE_TYPES = frozenset({"user", "group"})
SCOPE_TYPES = frozenset({"folder", "tag", "session"})


@dataclass(frozen=True)
class FolderRecord:
    folder_id: UUID
    tenant_id: UUID
    project_id: UUID
    name: str
    owner_user_id: UUID
    created_at: datetime
    parent_folder_id: UUID | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "folder_id": str(self.folder_id),
            "tenant_id": str(self.tenant_id),
            "project_id": str(self.project_id),
            "parent_folder_id": str(self.parent_folder_id) if self.parent_folder_id else None,
            "name": self.name,
            "owner_user_id": str(self.owner_user_id),
            "created_at": self.created_at.isoformat(),
        }


@dataclass(frozen=True)
class UserGroupRecord:
    group_id: UUID
    tenant_id: UUID
    name: str
    owner_user_id: UUID
    created_at: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "group_id": str(self.group_id),
            "tenant_id": str(self.tenant_id),
            "name": self.name,
            "owner_user_id": str(self.owner_user_id),
            "created_at": self.created_at.isoformat(),
        }


@dataclass(frozen=True)
class AccessGrantRecord:
    grant_id: UUID
    tenant_id: UUID
    grantee_type: str
    scope_type: str
    participant_role: str
    created_by: UUID
    created_at: datetime
    grantee_user_id: UUID | None = None
    grantee_group_id: UUID | None = None
    folder_id: UUID | None = None
    tag: str | None = None
    session_id: UUID | None = None
    expires_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "grant_id": str(self.grant_id),
            "tenant_id": str(self.tenant_id),
            "grantee_type": self.grantee_type,
            "grantee_user_id": str(self.grantee_user_id) if self.grantee_user_id else None,
            "grantee_group_id": str(self.grantee_group_id) if self.grantee_group_id else None,
            "scope_type": self.scope_type,
            "folder_id": str(self.folder_id) if self.folder_id else None,
            "tag": self.tag,
            "session_id": str(self.session_id) if self.session_id else None,
            "participant_role": self.participant_role,
            "created_by": str(self.created_by),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "created_at": self.created_at.isoformat(),
        }

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

CHAT_TURN_ROLES = frozenset(
    {
        "user",
        "classifier",
        "work_type_switch",
        "run_status",
        "theater",
        "system",
    }
)


@dataclass(frozen=True)
class ChatSessionRecord:
    session_id: UUID
    project_id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    title: str | None = None
    root_turn_id: UUID | None = None
    active_leaf_turn_id: UUID | None = None
    last_classification: dict[str, Any] | None = None
    work_type_override: str | None = None
    run_id: UUID | None = None
    campaign_id: UUID | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": str(self.session_id),
            "project_id": str(self.project_id),
            "tenant_id": str(self.tenant_id),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "title": self.title,
            "root_turn_id": str(self.root_turn_id) if self.root_turn_id else None,
            "active_leaf_turn_id": (
                str(self.active_leaf_turn_id) if self.active_leaf_turn_id else None
            ),
            "last_classification": self.last_classification,
            "work_type_override": self.work_type_override,
            "run_id": str(self.run_id) if self.run_id else None,
            "campaign_id": str(self.campaign_id) if self.campaign_id else None,
        }


@dataclass(frozen=True)
class ChatTurnRecord:
    turn_id: UUID
    session_id: UUID
    parent_turn_id: UUID | None
    ordinal: int
    role: str
    text: str
    payload: dict[str, Any]
    work_type: str | None = None
    work_type_source: str | None = None
    run_id: UUID | None = None
    campaign_id: UUID | None = None
    event_seq: int | None = None
    posted_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "turn_id": str(self.turn_id),
            "session_id": str(self.session_id),
            "parent_turn_id": str(self.parent_turn_id) if self.parent_turn_id else None,
            "ordinal": self.ordinal,
            "role": self.role,
            "text": self.text,
            "payload": self.payload,
            "work_type": self.work_type,
            "work_type_source": self.work_type_source,
            "run_id": str(self.run_id) if self.run_id else None,
            "campaign_id": str(self.campaign_id) if self.campaign_id else None,
            "event_seq": self.event_seq,
            "posted_at": self.posted_at.isoformat() if self.posted_at else None,
        }

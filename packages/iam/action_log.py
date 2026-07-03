from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


@dataclass(frozen=True)
class IamActionRecord:
    action_id: str
    occurred_at: datetime
    action: str
    tenant_id: str | None
    actor_key_id: str | None
    detail: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "occurred_at": self.occurred_at.isoformat(),
            "action": self.action,
            "tenant_id": self.tenant_id,
            "actor_key_id": self.actor_key_id,
            "detail": self.detail,
        }


def new_iam_action(
    *,
    action: str,
    tenant_id: str | None = None,
    actor_key_id: str | None = None,
    detail: dict[str, Any] | None = None,
) -> IamActionRecord:
    return IamActionRecord(
        action_id=str(uuid4()),
        occurred_at=datetime.now(timezone.utc),
        action=action,
        tenant_id=tenant_id,
        actor_key_id=actor_key_id,
        detail=detail or {},
    )

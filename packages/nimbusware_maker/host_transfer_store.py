from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4

from nimbusware_config.collab_policy_store import load_collab_policy
from nimbusware_env.dotenv import find_repo_root


class HostTransferRequest:
    def __init__(
        self,
        *,
        transfer_id: UUID,
        session_id: UUID,
        from_host_user_id: UUID,
        to_user_id: UUID,
        consent_expires_at: datetime,
        status: str = "pending",
    ) -> None:
        self.transfer_id = transfer_id
        self.session_id = session_id
        self.from_host_user_id = from_host_user_id
        self.to_user_id = to_user_id
        self.consent_expires_at = consent_expires_at
        self.status = status

    def to_dict(self) -> dict[str, Any]:
        return {
            "transfer_id": str(self.transfer_id),
            "session_id": str(self.session_id),
            "from_host_user_id": str(self.from_host_user_id),
            "to_user_id": str(self.to_user_id),
            "consent_expires_at": self.consent_expires_at.isoformat(),
            "status": self.status,
        }


class InMemoryHostTransferStore:
    def __init__(self) -> None:
        self._rows: dict[UUID, HostTransferRequest] = {}

    def create(
        self,
        *,
        session_id: UUID,
        from_host_user_id: UUID,
        to_user_id: UUID,
        consent_hours: int,
    ) -> HostTransferRequest:
        tid = uuid4()
        expires = datetime.now(timezone.utc) + timedelta(hours=consent_hours)
        row = HostTransferRequest(
            transfer_id=tid,
            session_id=session_id,
            from_host_user_id=from_host_user_id,
            to_user_id=to_user_id,
            consent_expires_at=expires,
        )
        self._rows[tid] = row
        return row

    def get(self, transfer_id: UUID) -> HostTransferRequest | None:
        return self._rows.get(transfer_id)

    def list_for_session(self, session_id: UUID) -> list[HostTransferRequest]:
        return [r for r in self._rows.values() if r.session_id == session_id]


_host_transfer_store = InMemoryHostTransferStore()


def host_transfer_store() -> InMemoryHostTransferStore:
    return _host_transfer_store


def default_consent_hours() -> int:
    policy = load_collab_policy(find_repo_root())
    raw = policy.get("host_transfer_consent_hours")
    if isinstance(raw, int) and raw > 0:
        return raw
    return 24

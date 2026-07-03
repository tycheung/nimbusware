from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Protocol
from uuid import UUID, uuid4

from config.collab_policy_store import load_collab_policy
from env.dotenv import find_repo_root
from maker.store_backend import build_cached_store


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


TRANSFER_STATUSES = frozenset(
    {
        "pending",
        "accepted",
        "declined",
        "expired",
        "frozen",
        "transferring",
        "completed",
        "cancelled",
    }
)


@dataclass
class HostTransferRequest:
    transfer_id: UUID
    session_id: UUID
    project_id: UUID
    from_host_user_id: UUID
    to_user_id: UUID
    initiated_by_user_id: UUID
    consent_expires_at: datetime
    status: str = "pending"
    direction: str = "host_nominate_successor"
    promote_to_admin: bool = False
    artifact_transfer_expires_at: datetime | None = None
    from_host_agreed_at: datetime | None = None
    freeze_started_at: datetime | None = None
    artifact_manifest: dict[str, Any] | None = None
    completed_at: datetime | None = None
    created_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "transfer_id": str(self.transfer_id),
            "session_id": str(self.session_id),
            "project_id": str(self.project_id),
            "from_host_user_id": str(self.from_host_user_id),
            "to_user_id": str(self.to_user_id),
            "initiated_by_user_id": str(self.initiated_by_user_id),
            "direction": self.direction,
            "promote_to_admin": self.promote_to_admin,
            "status": self.status,
            "consent_expires_at": self.consent_expires_at.isoformat(),
            "artifact_transfer_expires_at": (
                self.artifact_transfer_expires_at.isoformat()
                if self.artifact_transfer_expires_at
                else None
            ),
            "from_host_agreed_at": (
                self.from_host_agreed_at.isoformat() if self.from_host_agreed_at else None
            ),
            "freeze_started_at": (
                self.freeze_started_at.isoformat() if self.freeze_started_at else None
            ),
            "artifact_manifest": dict(self.artifact_manifest or {}),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


def _row_to_transfer(row: dict[str, Any]) -> HostTransferRequest:
    manifest = row.get("artifact_manifest")
    return HostTransferRequest(
        transfer_id=row["transfer_id"],
        session_id=row["session_id"],
        project_id=row["project_id"],
        from_host_user_id=row["from_host_user_id"],
        to_user_id=row["to_user_id"],
        initiated_by_user_id=row["initiated_by_user_id"],
        consent_expires_at=row["consent_expires_at"],
        status=str(row.get("status") or "pending"),
        direction=str(row.get("direction") or "host_nominate_successor"),
        promote_to_admin=bool(row.get("promote_to_admin")),
        artifact_transfer_expires_at=row.get("artifact_transfer_expires_at"),
        from_host_agreed_at=row.get("from_host_agreed_at"),
        freeze_started_at=row.get("freeze_started_at"),
        artifact_manifest=dict(manifest) if isinstance(manifest, dict) else {},
        completed_at=row.get("completed_at"),
        created_at=row.get("created_at"),
    )


class HostTransferStore(Protocol):
    def create(
        self,
        *,
        session_id: UUID,
        project_id: UUID,
        from_host_user_id: UUID,
        to_user_id: UUID,
        initiated_by_user_id: UUID,
        consent_hours: int,
    ) -> HostTransferRequest: ...

    def get(self, transfer_id: UUID) -> HostTransferRequest | None: ...

    def list_for_session(self, session_id: UUID) -> list[HostTransferRequest]: ...

    def accept_and_freeze(
        self,
        transfer_id: UUID,
        *,
        manifest: dict[str, Any],
    ) -> HostTransferRequest: ...

    def complete(self, transfer_id: UUID, *, new_host_user_id: UUID) -> HostTransferRequest: ...

    def decline(self, transfer_id: UUID) -> HostTransferRequest: ...

    def session_is_frozen(self, session_id: UUID) -> bool: ...


class InMemoryHostTransferStore:
    def __init__(self) -> None:
        self._rows: dict[UUID, HostTransferRequest] = {}
        self._frozen_sessions: set[UUID] = set()

    def create(
        self,
        *,
        session_id: UUID,
        project_id: UUID,
        from_host_user_id: UUID,
        to_user_id: UUID,
        initiated_by_user_id: UUID,
        consent_hours: int,
    ) -> HostTransferRequest:
        tid = uuid4()
        expires = _utc_now() + timedelta(hours=consent_hours)
        now = _utc_now()
        row = HostTransferRequest(
            transfer_id=tid,
            session_id=session_id,
            project_id=project_id,
            from_host_user_id=from_host_user_id,
            to_user_id=to_user_id,
            initiated_by_user_id=initiated_by_user_id,
            consent_expires_at=expires,
            created_at=now,
        )
        self._rows[tid] = row
        return row

    def get(self, transfer_id: UUID) -> HostTransferRequest | None:
        return self._rows.get(transfer_id)

    def list_for_session(self, session_id: UUID) -> list[HostTransferRequest]:
        return [r for r in self._rows.values() if r.session_id == session_id]

    def accept_and_freeze(
        self,
        transfer_id: UUID,
        *,
        manifest: dict[str, Any],
    ) -> HostTransferRequest:
        row = self._rows.get(transfer_id)
        if row is None:
            raise KeyError("transfer_not_found")
        now = _utc_now()
        updated = HostTransferRequest(
            transfer_id=row.transfer_id,
            session_id=row.session_id,
            project_id=row.project_id,
            from_host_user_id=row.from_host_user_id,
            to_user_id=row.to_user_id,
            initiated_by_user_id=row.initiated_by_user_id,
            consent_expires_at=row.consent_expires_at,
            status="frozen",
            direction=row.direction,
            promote_to_admin=row.promote_to_admin,
            from_host_agreed_at=now,
            freeze_started_at=now,
            artifact_manifest=dict(manifest),
            created_at=row.created_at,
        )
        self._rows[transfer_id] = updated
        self._frozen_sessions.add(row.session_id)
        return updated

    def complete(self, transfer_id: UUID, *, new_host_user_id: UUID) -> HostTransferRequest:
        row = self._rows.get(transfer_id)
        if row is None:
            raise KeyError("transfer_not_found")
        now = _utc_now()
        updated = HostTransferRequest(
            transfer_id=row.transfer_id,
            session_id=row.session_id,
            project_id=row.project_id,
            from_host_user_id=row.from_host_user_id,
            to_user_id=new_host_user_id,
            initiated_by_user_id=row.initiated_by_user_id,
            consent_expires_at=row.consent_expires_at,
            status="completed",
            direction=row.direction,
            promote_to_admin=row.promote_to_admin,
            from_host_agreed_at=row.from_host_agreed_at,
            freeze_started_at=row.freeze_started_at,
            artifact_manifest=dict(row.artifact_manifest or {}),
            completed_at=now,
            created_at=row.created_at,
        )
        self._rows[transfer_id] = updated
        self._frozen_sessions.discard(row.session_id)
        return updated

    def decline(self, transfer_id: UUID) -> HostTransferRequest:
        row = self._rows.get(transfer_id)
        if row is None:
            raise KeyError("transfer_not_found")
        updated = HostTransferRequest(
            transfer_id=row.transfer_id,
            session_id=row.session_id,
            project_id=row.project_id,
            from_host_user_id=row.from_host_user_id,
            to_user_id=row.to_user_id,
            initiated_by_user_id=row.initiated_by_user_id,
            consent_expires_at=row.consent_expires_at,
            status="declined",
            direction=row.direction,
            promote_to_admin=row.promote_to_admin,
            artifact_transfer_expires_at=row.artifact_transfer_expires_at,
            from_host_agreed_at=row.from_host_agreed_at,
            freeze_started_at=row.freeze_started_at,
            artifact_manifest=dict(row.artifact_manifest or {}),
            completed_at=row.completed_at,
            created_at=row.created_at,
        )
        self._rows[transfer_id] = updated
        return updated

    def session_is_frozen(self, session_id: UUID) -> bool:
        return session_id in self._frozen_sessions


_store: list[InMemoryHostTransferStore | None] = [None]


def build_host_transfer_store(database_url: str | None) -> HostTransferStore:
    def _postgres(url: str) -> HostTransferStore:
        from maker.host_transfer_store_postgres import PostgresHostTransferStore

        return PostgresHostTransferStore(url)

    return build_cached_store(
        database_url,
        cache=_store,
        memory_factory=InMemoryHostTransferStore,
        postgres_factory=_postgres,  # type: ignore[arg-type]
    )


def host_transfer_store() -> HostTransferStore:
    return build_host_transfer_store(None)


def default_consent_hours() -> int:
    policy = load_collab_policy(find_repo_root())
    raw = policy.get("host_transfer_consent_hours")
    if isinstance(raw, int) and raw > 0:
        return raw
    return 24

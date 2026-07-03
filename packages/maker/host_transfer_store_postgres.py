from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from maker.host_transfer_store import (
    HostTransferRequest,
    _row_to_transfer,
    _utc_now,
)


class PostgresHostTransferStore:
    def __init__(self, database_url: str) -> None:
        self._url = database_url

    def _conn(self) -> psycopg.Connection[Any]:
        return psycopg.connect(self._url)

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
        from datetime import timedelta

        tid = uuid4()
        expires = _utc_now() + timedelta(hours=consent_hours)
        now = _utc_now()
        with self._conn() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                INSERT INTO nimbusware_host_transfer_request (
                  transfer_id, session_id, project_id, from_host_user_id, to_user_id,
                  initiated_by_user_id, consent_expires_at, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *
                """,
                (
                    tid,
                    session_id,
                    project_id,
                    from_host_user_id,
                    to_user_id,
                    initiated_by_user_id,
                    expires,
                    now,
                ),
            )
            row = cur.fetchone()
            conn.commit()
        assert row is not None
        return _row_to_transfer(row)

    def get(self, transfer_id: UUID) -> HostTransferRequest | None:
        with self._conn() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT * FROM nimbusware_host_transfer_request WHERE transfer_id = %s",
                (transfer_id,),
            )
            row = cur.fetchone()
        return _row_to_transfer(row) if row else None

    def list_for_session(self, session_id: UUID) -> list[HostTransferRequest]:
        with self._conn() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT * FROM nimbusware_host_transfer_request
                WHERE session_id = %s
                ORDER BY created_at DESC
                """,
                (session_id,),
            )
            rows = cur.fetchall()
        return [_row_to_transfer(r) for r in rows]

    def accept_and_freeze(
        self,
        transfer_id: UUID,
        *,
        manifest: dict[str, Any],
    ) -> HostTransferRequest:
        now = _utc_now()
        with self._conn() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                UPDATE nimbusware_host_transfer_request SET
                  status = 'frozen',
                  from_host_agreed_at = %s,
                  freeze_started_at = %s,
                  artifact_manifest = %s::jsonb
                WHERE transfer_id = %s
                RETURNING *
                """,
                (now, now, Jsonb(manifest), transfer_id),
            )
            row = cur.fetchone()
            if row is None:
                raise KeyError("transfer_not_found")
            conn.commit()
        return _row_to_transfer(row)

    def complete(self, transfer_id: UUID, *, new_host_user_id: UUID) -> HostTransferRequest:
        now = _utc_now()
        with self._conn() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                UPDATE nimbusware_host_transfer_request SET
                  status = 'completed',
                  to_user_id = %s,
                  completed_at = %s
                WHERE transfer_id = %s
                RETURNING *
                """,
                (new_host_user_id, now, transfer_id),
            )
            row = cur.fetchone()
            if row is None:
                raise KeyError("transfer_not_found")
            conn.commit()
        return _row_to_transfer(row)

    def decline(self, transfer_id: UUID) -> HostTransferRequest:
        with self._conn() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                UPDATE nimbusware_host_transfer_request SET status = 'declined'
                WHERE transfer_id = %s AND status = 'pending'
                RETURNING *
                """,
                (transfer_id,),
            )
            row = cur.fetchone()
            if row is None:
                raise KeyError("transfer_not_found")
            conn.commit()
        return _row_to_transfer(row)

    def session_is_frozen(self, session_id: UUID) -> bool:
        with self._conn() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT 1 FROM nimbusware_host_transfer_request
                WHERE session_id = %s AND status IN ('frozen', 'transferring')
                LIMIT 1
                """,
                (session_id,),
            )
            return cur.fetchone() is not None

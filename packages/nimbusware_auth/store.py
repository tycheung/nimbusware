from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

import psycopg
from psycopg.rows import dict_row

from nimbusware_auth.crypto import hash_password
from nimbusware_auth.models import (
    InviteRecord,
    ParticipantRecord,
    SESSION_PARTICIPANT_ROLES,
    UserRecord,
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _hash_invite_token(token: str) -> str:
    import hashlib

    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class InMemoryUserStore:
    def __init__(self) -> None:
        self._users: dict[UUID, UserRecord] = {}
        self._by_username: dict[str, UUID] = {}

    def count_users(self) -> int:
        return len(self._users)

    def create_user(
        self,
        *,
        username: str,
        password: str,
        display_name: str = "",
    ) -> UserRecord:
        name = username.strip().lower()
        if not name:
            raise ValueError("username_required")
        if name in self._by_username:
            raise ValueError("username_taken")
        uid = uuid4()
        now = _utc_now()
        is_owner = len(self._users) == 0
        row = UserRecord(
            user_id=uid,
            username=name,
            display_name=(display_name.strip() or name),
            password_hash=hash_password(password),
            created_at=now,
            is_owner=is_owner,
        )
        self._users[uid] = row
        self._by_username[name] = uid
        return row

    def get_user(self, user_id: UUID) -> UserRecord | None:
        return self._users.get(user_id)

    def get_user_by_username(self, username: str) -> UserRecord | None:
        uid = self._by_username.get(username.strip().lower())
        return self._users.get(uid) if uid else None

    def search_users(self, *, query: str, limit: int = 20) -> list[UserRecord]:
        q = query.strip().lower()
        rows = list(self._users.values())
        if q:
            rows = [
                u
                for u in rows
                if q in u.username.lower() or q in u.display_name.lower()
            ]
        return sorted(rows, key=lambda u: u.username)[: max(1, min(limit, 100))]


class PostgresUserStore:
    def __init__(self, database_url: str) -> None:
        self._url = database_url

    def _conn(self) -> psycopg.Connection[Any]:
        return psycopg.connect(self._url)

    def count_users(self) -> int:
        with self._conn() as conn, conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM nimbusware_user")
            row = cur.fetchone()
        return int(row[0]) if row else 0

    def create_user(
        self,
        *,
        username: str,
        password: str,
        display_name: str = "",
    ) -> UserRecord:
        name = username.strip().lower()
        if not name:
            raise ValueError("username_required")
        uid = uuid4()
        now = _utc_now()
        is_owner = self.count_users() == 0
        digest = hash_password(password)
        disp = display_name.strip() or name
        with self._conn() as conn, conn.cursor(row_factory=dict_row) as cur:
            try:
                cur.execute(
                    """
                    INSERT INTO nimbusware_user (
                      user_id, username, password_hash, display_name, is_owner, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING *
                    """,
                    (uid, name, digest, disp, is_owner, now),
                )
            except psycopg.errors.UniqueViolation as exc:
                raise ValueError("username_taken") from exc
            row = cur.fetchone()
            conn.commit()
        assert row is not None
        return _user_from_row(row)

    def get_user(self, user_id: UUID) -> UserRecord | None:
        with self._conn() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT * FROM nimbusware_user WHERE user_id = %s", (user_id,))
            row = cur.fetchone()
        return _user_from_row(row) if row else None

    def get_user_by_username(self, username: str) -> UserRecord | None:
        name = username.strip().lower()
        with self._conn() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT * FROM nimbusware_user WHERE username = %s", (name,))
            row = cur.fetchone()
        return _user_from_row(row) if row else None

    def search_users(self, *, query: str, limit: int = 20) -> list[UserRecord]:
        q = f"%{query.strip().lower()}%"
        cap = max(1, min(limit, 100))
        with self._conn() as conn, conn.cursor(row_factory=dict_row) as cur:
            if query.strip():
                cur.execute(
                    """
                    SELECT * FROM nimbusware_user
                    WHERE LOWER(username) LIKE %s OR LOWER(display_name) LIKE %s
                    ORDER BY username ASC
                    LIMIT %s
                    """,
                    (q, q, cap),
                )
            else:
                cur.execute(
                    "SELECT * FROM nimbusware_user ORDER BY username ASC LIMIT %s",
                    (cap,),
                )
            rows = cur.fetchall()
        return [_user_from_row(r) for r in rows]


def _user_from_row(row: dict[str, object]) -> UserRecord:
    return UserRecord(
        user_id=row["user_id"],  # type: ignore[arg-type]
        username=str(row["username"]),
        display_name=str(row.get("display_name") or row["username"]),
        password_hash=str(row["password_hash"]),
        created_at=row["created_at"],  # type: ignore[arg-type]
        is_owner=bool(row.get("is_owner")),
    )


UserStore = InMemoryUserStore | PostgresUserStore


def build_user_store(database_url: str | None) -> UserStore:
    if database_url:
        return PostgresUserStore(database_url)
    return InMemoryUserStore()


class InMemoryCollabStore:
    def __init__(self, user_store: InMemoryUserStore) -> None:
        self._users = user_store
        self._participants: dict[tuple[UUID, UUID], ParticipantRecord] = {}
        self._invites: dict[str, InviteRecord] = {}
        self._invite_by_id: dict[UUID, InviteRecord] = {}

    def list_participants(self, session_id: UUID) -> list[ParticipantRecord]:
        rows = [p for (sid, _), p in self._participants.items() if sid == session_id]
        return sorted(rows, key=lambda p: p.joined_at)

    def get_participant(self, session_id: UUID, user_id: UUID) -> ParticipantRecord | None:
        return self._participants.get((session_id, user_id))

    def add_participant(
        self,
        *,
        session_id: UUID,
        user_id: UUID,
        role: str,
    ) -> ParticipantRecord:
        role_n = role.strip().lower()
        if role_n not in SESSION_PARTICIPANT_ROLES:
            raise ValueError("invalid_participant_role")
        now = _utc_now()
        user = self._users.get_user(user_id)
        row = ParticipantRecord(
            session_id=session_id,
            user_id=user_id,
            role=role_n,
            joined_at=now,
            username=user.username if user else None,
            display_name=user.display_name if user else None,
        )
        self._participants[(session_id, user_id)] = row
        return row

    def remove_participant(self, session_id: UUID, user_id: UUID) -> bool:
        return self._participants.pop((session_id, user_id), None) is not None

    def create_invite(
        self,
        *,
        session_id: UUID,
        role: str,
        created_by: UUID,
        expires_at: datetime,
    ) -> InviteRecord:
        import secrets

        role_n = role.strip().lower()
        if role_n not in SESSION_PARTICIPANT_ROLES:
            raise ValueError("invalid_participant_role")
        token = secrets.token_urlsafe(32)
        iid = uuid4()
        now = _utc_now()
        row = InviteRecord(
            invite_id=iid,
            session_id=session_id,
            role=role_n,
            token=token,
            expires_at=expires_at,
            created_by=created_by,
            created_at=now,
        )
        self._invites[token] = row
        self._invite_by_id[iid] = row
        return row

    def consume_invite(self, token: str) -> InviteRecord | None:
        row = self._invites.pop(token, None)
        if row is None:
            return None
        self._invite_by_id.pop(row.invite_id, None)
        if row.expires_at < _utc_now():
            return None
        return row


class PostgresCollabStore:
    def __init__(self, database_url: str, user_store: PostgresUserStore) -> None:
        self._url = database_url
        self._users = user_store

    def _conn(self) -> psycopg.Connection[Any]:
        return psycopg.connect(self._url)

    def list_participants(self, session_id: UUID) -> list[ParticipantRecord]:
        with self._conn() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT p.*, u.username, u.display_name
                FROM nimbusware_chat_participant p
                LEFT JOIN nimbusware_user u ON u.user_id = p.user_id
                WHERE p.session_id = %s
                ORDER BY p.joined_at ASC
                """,
                (session_id,),
            )
            rows = cur.fetchall()
        return [_participant_from_row(r) for r in rows]

    def get_participant(self, session_id: UUID, user_id: UUID) -> ParticipantRecord | None:
        with self._conn() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT p.*, u.username, u.display_name
                FROM nimbusware_chat_participant p
                LEFT JOIN nimbusware_user u ON u.user_id = p.user_id
                WHERE p.session_id = %s AND p.user_id = %s
                """,
                (session_id, user_id),
            )
            row = cur.fetchone()
        return _participant_from_row(row) if row else None

    def add_participant(
        self,
        *,
        session_id: UUID,
        user_id: UUID,
        role: str,
    ) -> ParticipantRecord:
        role_n = role.strip().lower()
        if role_n not in SESSION_PARTICIPANT_ROLES:
            raise ValueError("invalid_participant_role")
        now = _utc_now()
        with self._conn() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                INSERT INTO nimbusware_chat_participant (session_id, user_id, role, joined_at)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (session_id, user_id) DO UPDATE SET role = EXCLUDED.role
                RETURNING session_id, user_id, role, joined_at
                """,
                (session_id, user_id, role_n, now),
            )
            row = cur.fetchone()
            cur.execute(
                "SELECT username, display_name FROM nimbusware_user WHERE user_id = %s",
                (user_id,),
            )
            user_row = cur.fetchone()
            conn.commit()
        assert row is not None
        return ParticipantRecord(
            session_id=session_id,
            user_id=user_id,
            role=role_n,
            joined_at=row["joined_at"],  # type: ignore[arg-type]
            username=str(user_row["username"]) if user_row else None,
            display_name=str(user_row["display_name"]) if user_row else None,
        )

    def remove_participant(self, session_id: UUID, user_id: UUID) -> bool:
        with self._conn() as conn, conn.cursor() as cur:
            cur.execute(
                "DELETE FROM nimbusware_chat_participant WHERE session_id = %s AND user_id = %s",
                (session_id, user_id),
            )
            deleted = cur.rowcount > 0
            conn.commit()
        return deleted

    def create_invite(
        self,
        *,
        session_id: UUID,
        role: str,
        created_by: UUID,
        expires_at: datetime,
    ) -> InviteRecord:
        import secrets

        role_n = role.strip().lower()
        if role_n not in SESSION_PARTICIPANT_ROLES:
            raise ValueError("invalid_participant_role")
        token = secrets.token_urlsafe(32)
        iid = uuid4()
        now = _utc_now()
        digest = _hash_invite_token(token)
        with self._conn() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO nimbusware_chat_invite (
                  invite_id, session_id, token_hash, role, expires_at, created_by, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (iid, session_id, digest, role_n, expires_at, created_by, now),
            )
            conn.commit()
        return InviteRecord(
            invite_id=iid,
            session_id=session_id,
            role=role_n,
            token=token,
            expires_at=expires_at,
            created_by=created_by,
            created_at=now,
        )

    def consume_invite(self, token: str) -> InviteRecord | None:
        digest = _hash_invite_token(token)
        now = _utc_now()
        with self._conn() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT * FROM nimbusware_chat_invite
                WHERE token_hash = %s AND consumed_at IS NULL AND expires_at > %s
                FOR UPDATE
                """,
                (digest, now),
            )
            row = cur.fetchone()
            if row is None:
                return None
            cur.execute(
                "UPDATE nimbusware_chat_invite SET consumed_at = %s WHERE invite_id = %s",
                (now, row["invite_id"]),
            )
            conn.commit()
        return InviteRecord(
            invite_id=row["invite_id"],  # type: ignore[arg-type]
            session_id=row["session_id"],  # type: ignore[arg-type]
            role=str(row["role"]),
            token=token,
            expires_at=row["expires_at"],  # type: ignore[arg-type]
            created_by=row["created_by"],  # type: ignore[arg-type]
            created_at=row["created_at"],  # type: ignore[arg-type]
        )


def _participant_from_row(row: dict[str, object]) -> ParticipantRecord:
    return ParticipantRecord(
        session_id=row["session_id"],  # type: ignore[arg-type]
        user_id=row["user_id"],  # type: ignore[arg-type]
        role=str(row["role"]),
        joined_at=row["joined_at"],  # type: ignore[arg-type]
        username=str(row["username"]) if row.get("username") else None,
        display_name=str(row["display_name"]) if row.get("display_name") else None,
    )


CollabStore = InMemoryCollabStore | PostgresCollabStore


def build_collab_store(
    database_url: str | None,
    user_store: UserStore,
) -> CollabStore:
    if database_url and isinstance(user_store, PostgresUserStore):
        return PostgresCollabStore(database_url, user_store)
    if isinstance(user_store, InMemoryUserStore):
        return InMemoryCollabStore(user_store)
    return InMemoryCollabStore(InMemoryUserStore())

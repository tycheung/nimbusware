from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Protocol
from uuid import UUID, uuid4

import psycopg
from psycopg.rows import dict_row

from nimbusware_auth.models import SESSION_PARTICIPANT_ROLES
from nimbusware_iam.constants import DEFAULT_TENANT_ID
from nimbusware_maker.chat_library_models import (
    GRANTEE_TYPES,
    SCOPE_TYPES,
    AccessGrantRecord,
    FolderRecord,
    UserGroupRecord,
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ChatLibraryStore(Protocol):
    def create_folder(
        self,
        *,
        project_id: UUID,
        name: str,
        owner_user_id: UUID,
        tenant_id: UUID | None = None,
        parent_folder_id: UUID | None = None,
    ) -> FolderRecord: ...

    def list_folders(self, *, project_id: UUID) -> list[FolderRecord]: ...

    def get_folder(self, folder_id: UUID) -> FolderRecord | None: ...

    def update_folder(
        self,
        folder_id: UUID,
        *,
        name: str | None = None,
        parent_folder_id: UUID | None = None,
    ) -> FolderRecord: ...

    def delete_folder(self, folder_id: UUID) -> bool: ...

    def create_group(
        self,
        *,
        name: str,
        owner_user_id: UUID,
        tenant_id: UUID | None = None,
    ) -> UserGroupRecord: ...

    def list_groups(self, *, tenant_id: UUID | None = None) -> list[UserGroupRecord]: ...

    def add_group_member(self, group_id: UUID, user_id: UUID) -> None: ...

    def list_group_members(self, group_id: UUID) -> list[UUID]: ...

    def create_grant(
        self,
        *,
        grantee_type: str,
        scope_type: str,
        participant_role: str,
        created_by: UUID,
        tenant_id: UUID | None = None,
        grantee_user_id: UUID | None = None,
        grantee_group_id: UUID | None = None,
        folder_id: UUID | None = None,
        tag: str | None = None,
        session_id: UUID | None = None,
        expires_at: datetime | None = None,
    ) -> AccessGrantRecord: ...

    def list_grants(
        self,
        *,
        project_id: UUID | None = None,
        folder_id: UUID | None = None,
        session_id: UUID | None = None,
    ) -> list[AccessGrantRecord]: ...

    def delete_grant(self, grant_id: UUID) -> bool: ...

    def grant_roles_for_user(
        self,
        *,
        user_id: UUID,
        session_id: UUID,
        folder_id: UUID | None,
        tags: list[str],
        group_ids: list[UUID] | None = None,
    ) -> tuple[list[str], list[str], list[str]]: ...


def _folder_from_row(row: dict[str, Any]) -> FolderRecord:
    return FolderRecord(
        folder_id=row["folder_id"],
        tenant_id=row["tenant_id"],
        project_id=row["project_id"],
        name=str(row["name"]),
        owner_user_id=row["owner_user_id"],
        created_at=row["created_at"],
        parent_folder_id=row.get("parent_folder_id"),
    )


def _group_from_row(row: dict[str, Any]) -> UserGroupRecord:
    return UserGroupRecord(
        group_id=row["group_id"],
        tenant_id=row["tenant_id"],
        name=str(row["name"]),
        owner_user_id=row["owner_user_id"],
        created_at=row["created_at"],
    )


def _grant_from_row(row: dict[str, Any]) -> AccessGrantRecord:
    return AccessGrantRecord(
        grant_id=row["grant_id"],
        tenant_id=row["tenant_id"],
        grantee_type=str(row["grantee_type"]),
        grantee_user_id=row.get("grantee_user_id"),
        grantee_group_id=row.get("grantee_group_id"),
        scope_type=str(row["scope_type"]),
        folder_id=row.get("folder_id"),
        tag=str(row["tag"]) if row.get("tag") else None,
        session_id=row.get("session_id"),
        participant_role=str(row["participant_role"]),
        created_by=row["created_by"],
        expires_at=row.get("expires_at"),
        created_at=row["created_at"],
    )


def _validate_grant_inputs(
    *,
    grantee_type: str,
    scope_type: str,
    participant_role: str,
    grantee_user_id: UUID | None,
    grantee_group_id: UUID | None,
    folder_id: UUID | None,
    tag: str | None,
    session_id: UUID | None,
) -> None:
    if grantee_type not in GRANTEE_TYPES:
        raise ValueError("invalid_grantee_type")
    if scope_type not in SCOPE_TYPES:
        raise ValueError("invalid_scope_type")
    if participant_role not in SESSION_PARTICIPANT_ROLES:
        raise ValueError("invalid_participant_role")
    if grantee_type == "user" and grantee_user_id is None:
        raise ValueError("grantee_user_required")
    if grantee_type == "group" and grantee_group_id is None:
        raise ValueError("grantee_group_required")
    if scope_type == "folder" and folder_id is None:
        raise ValueError("folder_id_required")
    if scope_type == "tag" and not (tag and tag.strip()):
        raise ValueError("tag_required")
    if scope_type == "session" and session_id is None:
        raise ValueError("session_id_required")


class InMemoryChatLibraryStore:
    def __init__(self) -> None:
        self._folders: dict[UUID, FolderRecord] = {}
        self._groups: dict[UUID, UserGroupRecord] = {}
        self._group_members: dict[UUID, set[UUID]] = {}
        self._grants: dict[UUID, AccessGrantRecord] = {}

    def create_folder(
        self,
        *,
        project_id: UUID,
        name: str,
        owner_user_id: UUID,
        tenant_id: UUID | None = None,
        parent_folder_id: UUID | None = None,
    ) -> FolderRecord:
        fid = uuid4()
        now = _utc_now()
        row = FolderRecord(
            folder_id=fid,
            tenant_id=tenant_id or DEFAULT_TENANT_ID,
            project_id=project_id,
            name=name.strip(),
            owner_user_id=owner_user_id,
            created_at=now,
            parent_folder_id=parent_folder_id,
        )
        self._folders[fid] = row
        return row

    def list_folders(self, *, project_id: UUID) -> list[FolderRecord]:
        rows = [f for f in self._folders.values() if f.project_id == project_id]
        return sorted(rows, key=lambda f: f.name.lower())

    def get_folder(self, folder_id: UUID) -> FolderRecord | None:
        return self._folders.get(folder_id)

    def update_folder(
        self,
        folder_id: UUID,
        *,
        name: str | None = None,
        parent_folder_id: UUID | None = None,
    ) -> FolderRecord:
        row = self._folders.get(folder_id)
        if row is None:
            raise KeyError("folder_not_found")
        updated = FolderRecord(
            folder_id=row.folder_id,
            tenant_id=row.tenant_id,
            project_id=row.project_id,
            name=name.strip() if name is not None else row.name,
            owner_user_id=row.owner_user_id,
            created_at=row.created_at,
            parent_folder_id=parent_folder_id if parent_folder_id is not None else row.parent_folder_id,
        )
        self._folders[folder_id] = updated
        return updated

    def delete_folder(self, folder_id: UUID) -> bool:
        return self._folders.pop(folder_id, None) is not None

    def create_group(
        self,
        *,
        name: str,
        owner_user_id: UUID,
        tenant_id: UUID | None = None,
    ) -> UserGroupRecord:
        gid = uuid4()
        now = _utc_now()
        row = UserGroupRecord(
            group_id=gid,
            tenant_id=tenant_id or DEFAULT_TENANT_ID,
            name=name.strip(),
            owner_user_id=owner_user_id,
            created_at=now,
        )
        self._groups[gid] = row
        self._group_members[gid] = set()
        return row

    def list_groups(self, *, tenant_id: UUID | None = None) -> list[UserGroupRecord]:
        tid = tenant_id or DEFAULT_TENANT_ID
        rows = [g for g in self._groups.values() if g.tenant_id == tid]
        return sorted(rows, key=lambda g: g.name.lower())

    def add_group_member(self, group_id: UUID, user_id: UUID) -> None:
        if group_id not in self._groups:
            raise KeyError("group_not_found")
        self._group_members.setdefault(group_id, set()).add(user_id)

    def list_group_members(self, group_id: UUID) -> list[UUID]:
        return sorted(self._group_members.get(group_id, set()), key=str)

    def create_grant(
        self,
        *,
        grantee_type: str,
        scope_type: str,
        participant_role: str,
        created_by: UUID,
        tenant_id: UUID | None = None,
        grantee_user_id: UUID | None = None,
        grantee_group_id: UUID | None = None,
        folder_id: UUID | None = None,
        tag: str | None = None,
        session_id: UUID | None = None,
        expires_at: datetime | None = None,
    ) -> AccessGrantRecord:
        _validate_grant_inputs(
            grantee_type=grantee_type,
            scope_type=scope_type,
            participant_role=participant_role,
            grantee_user_id=grantee_user_id,
            grantee_group_id=grantee_group_id,
            folder_id=folder_id,
            tag=tag,
            session_id=session_id,
        )
        gid = uuid4()
        now = _utc_now()
        row = AccessGrantRecord(
            grant_id=gid,
            tenant_id=tenant_id or DEFAULT_TENANT_ID,
            grantee_type=grantee_type,
            grantee_user_id=grantee_user_id,
            grantee_group_id=grantee_group_id,
            scope_type=scope_type,
            folder_id=folder_id,
            tag=tag.strip() if tag else None,
            session_id=session_id,
            participant_role=participant_role,
            created_by=created_by,
            expires_at=expires_at,
            created_at=now,
        )
        self._grants[gid] = row
        return row

    def list_grants(
        self,
        *,
        project_id: UUID | None = None,
        folder_id: UUID | None = None,
        session_id: UUID | None = None,
    ) -> list[AccessGrantRecord]:
        rows = list(self._grants.values())
        if folder_id is not None:
            rows = [g for g in rows if g.folder_id == folder_id]
        if session_id is not None:
            rows = [g for g in rows if g.session_id == session_id]
        if project_id is not None:
            folder_ids = {f.folder_id for f in self._folders.values() if f.project_id == project_id}
            rows = [
                g
                for g in rows
                if g.scope_type != "folder" or (g.folder_id and g.folder_id in folder_ids)
            ]
        return sorted(rows, key=lambda g: g.created_at)

    def delete_grant(self, grant_id: UUID) -> bool:
        return self._grants.pop(grant_id, None) is not None

    def grant_roles_for_user(
        self,
        *,
        user_id: UUID,
        session_id: UUID,
        folder_id: UUID | None,
        tags: list[str],
        group_ids: list[UUID] | None = None,
    ) -> tuple[list[str], list[str], list[str]]:
        now = _utc_now()
        session_roles: list[str] = []
        folder_roles: list[str] = []
        tag_roles: list[str] = []
        member_groups = set(group_ids or [])
        for g in self._grants.values():
            if g.expires_at is not None and g.expires_at < now:
                continue
            applies = False
            if g.grantee_type == "user" and g.grantee_user_id == user_id:
                applies = True
            elif g.grantee_type == "group" and g.grantee_group_id in member_groups:
                applies = True
            elif g.grantee_type == "group" and g.grantee_group_id is not None:
                if user_id in self._group_members.get(g.grantee_group_id, set()):
                    applies = True
            if not applies:
                continue
            if g.scope_type == "session" and g.session_id == session_id:
                session_roles.append(g.participant_role)
            elif g.scope_type == "folder" and folder_id and g.folder_id == folder_id:
                folder_roles.append(g.participant_role)
            elif g.scope_type == "tag" and g.tag and g.tag in tags:
                tag_roles.append(g.participant_role)
        return session_roles, folder_roles, tag_roles


class PostgresChatLibraryStore:
    def __init__(self, database_url: str) -> None:
        self._url = database_url

    def _conn(self) -> psycopg.Connection[Any]:
        return psycopg.connect(self._url)

    def create_folder(
        self,
        *,
        project_id: UUID,
        name: str,
        owner_user_id: UUID,
        tenant_id: UUID | None = None,
        parent_folder_id: UUID | None = None,
    ) -> FolderRecord:
        fid = uuid4()
        now = _utc_now()
        tid = tenant_id or DEFAULT_TENANT_ID
        with self._conn() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                INSERT INTO nimbusware_chat_folder (
                  folder_id, tenant_id, project_id, parent_folder_id, name, owner_user_id, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING *
                """,
                (fid, tid, project_id, parent_folder_id, name.strip(), owner_user_id, now),
            )
            row = cur.fetchone()
            conn.commit()
        assert row is not None
        return _folder_from_row(row)

    def list_folders(self, *, project_id: UUID) -> list[FolderRecord]:
        with self._conn() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT * FROM nimbusware_chat_folder
                WHERE project_id = %s
                ORDER BY name ASC
                """,
                (project_id,),
            )
            rows = cur.fetchall()
        return [_folder_from_row(r) for r in rows]

    def get_folder(self, folder_id: UUID) -> FolderRecord | None:
        with self._conn() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT * FROM nimbusware_chat_folder WHERE folder_id = %s",
                (folder_id,),
            )
            row = cur.fetchone()
        return _folder_from_row(row) if row else None

    def update_folder(
        self,
        folder_id: UUID,
        *,
        name: str | None = None,
        parent_folder_id: UUID | None = None,
    ) -> FolderRecord:
        with self._conn() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                UPDATE nimbusware_chat_folder SET
                  name = COALESCE(%s, name),
                  parent_folder_id = COALESCE(%s, parent_folder_id)
                WHERE folder_id = %s
                RETURNING *
                """,
                (name.strip() if name is not None else None, parent_folder_id, folder_id),
            )
            row = cur.fetchone()
            if row is None:
                raise KeyError("folder_not_found")
            conn.commit()
        return _folder_from_row(row)

    def delete_folder(self, folder_id: UUID) -> bool:
        with self._conn() as conn, conn.cursor() as cur:
            cur.execute(
                "DELETE FROM nimbusware_chat_folder WHERE folder_id = %s",
                (folder_id,),
            )
            deleted = cur.rowcount > 0
            conn.commit()
        return deleted

    def create_group(
        self,
        *,
        name: str,
        owner_user_id: UUID,
        tenant_id: UUID | None = None,
    ) -> UserGroupRecord:
        gid = uuid4()
        now = _utc_now()
        tid = tenant_id or DEFAULT_TENANT_ID
        with self._conn() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                INSERT INTO nimbusware_user_group (group_id, tenant_id, name, owner_user_id, created_at)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING *
                """,
                (gid, tid, name.strip(), owner_user_id, now),
            )
            row = cur.fetchone()
            conn.commit()
        assert row is not None
        return _group_from_row(row)

    def list_groups(self, *, tenant_id: UUID | None = None) -> list[UserGroupRecord]:
        tid = tenant_id or DEFAULT_TENANT_ID
        with self._conn() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT * FROM nimbusware_user_group WHERE tenant_id = %s ORDER BY name ASC",
                (tid,),
            )
            rows = cur.fetchall()
        return [_group_from_row(r) for r in rows]

    def add_group_member(self, group_id: UUID, user_id: UUID) -> None:
        with self._conn() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO nimbusware_user_group_member (group_id, user_id)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
                """,
                (group_id, user_id),
            )
            conn.commit()

    def list_group_members(self, group_id: UUID) -> list[UUID]:
        with self._conn() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT user_id FROM nimbusware_user_group_member WHERE group_id = %s",
                (group_id,),
            )
            rows = cur.fetchall()
        return [r["user_id"] for r in rows]

    def create_grant(
        self,
        *,
        grantee_type: str,
        scope_type: str,
        participant_role: str,
        created_by: UUID,
        tenant_id: UUID | None = None,
        grantee_user_id: UUID | None = None,
        grantee_group_id: UUID | None = None,
        folder_id: UUID | None = None,
        tag: str | None = None,
        session_id: UUID | None = None,
        expires_at: datetime | None = None,
    ) -> AccessGrantRecord:
        _validate_grant_inputs(
            grantee_type=grantee_type,
            scope_type=scope_type,
            participant_role=participant_role,
            grantee_user_id=grantee_user_id,
            grantee_group_id=grantee_group_id,
            folder_id=folder_id,
            tag=tag,
            session_id=session_id,
        )
        gid = uuid4()
        now = _utc_now()
        tid = tenant_id or DEFAULT_TENANT_ID
        with self._conn() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                INSERT INTO nimbusware_chat_access_grant (
                  grant_id, tenant_id, grantee_type, grantee_user_id, grantee_group_id,
                  scope_type, folder_id, tag, session_id, participant_role,
                  created_by, expires_at, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *
                """,
                (
                    gid,
                    tid,
                    grantee_type,
                    grantee_user_id,
                    grantee_group_id,
                    scope_type,
                    folder_id,
                    tag.strip() if tag else None,
                    session_id,
                    participant_role,
                    created_by,
                    expires_at,
                    now,
                ),
            )
            row = cur.fetchone()
            conn.commit()
        assert row is not None
        return _grant_from_row(row)

    def list_grants(
        self,
        *,
        project_id: UUID | None = None,
        folder_id: UUID | None = None,
        session_id: UUID | None = None,
    ) -> list[AccessGrantRecord]:
        clauses: list[str] = []
        params: list[Any] = []
        if folder_id is not None:
            clauses.append("folder_id = %s")
            params.append(folder_id)
        if session_id is not None:
            clauses.append("session_id = %s")
            params.append(session_id)
        if project_id is not None:
            clauses.append(
                """(
                  scope_type != 'folder'
                  OR folder_id IN (
                    SELECT folder_id FROM nimbusware_chat_folder WHERE project_id = %s
                  )
                )"""
            )
            params.append(project_id)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._conn() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                f"SELECT * FROM nimbusware_chat_access_grant {where} ORDER BY created_at ASC",
                tuple(params),
            )
            rows = cur.fetchall()
        return [_grant_from_row(r) for r in rows]

    def delete_grant(self, grant_id: UUID) -> bool:
        with self._conn() as conn, conn.cursor() as cur:
            cur.execute(
                "DELETE FROM nimbusware_chat_access_grant WHERE grant_id = %s",
                (grant_id,),
            )
            deleted = cur.rowcount > 0
            conn.commit()
        return deleted

    def grant_roles_for_user(
        self,
        *,
        user_id: UUID,
        session_id: UUID,
        folder_id: UUID | None,
        tags: list[str],
        group_ids: list[UUID] | None = None,
    ) -> tuple[list[str], list[str], list[str]]:
        with self._conn() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT g.participant_role, g.scope_type, g.folder_id, g.tag, g.session_id
                FROM nimbusware_chat_access_grant g
                WHERE (g.expires_at IS NULL OR g.expires_at > NOW())
                  AND (
                    (g.grantee_type = 'user' AND g.grantee_user_id = %s)
                    OR (
                      g.grantee_type = 'group'
                      AND g.grantee_group_id IN (
                        SELECT group_id FROM nimbusware_user_group_member WHERE user_id = %s
                      )
                    )
                  )
                """,
                (user_id, user_id),
            )
            rows = cur.fetchall()
        session_roles: list[str] = []
        folder_roles: list[str] = []
        tag_roles: list[str] = []
        tag_set = set(tags)
        for row in rows:
            role = str(row["participant_role"])
            scope = str(row["scope_type"])
            if scope == "session" and row["session_id"] == session_id:
                session_roles.append(role)
            elif scope == "folder" and folder_id and row["folder_id"] == folder_id:
                folder_roles.append(role)
            elif scope == "tag" and row["tag"] and row["tag"] in tag_set:
                tag_roles.append(role)
        return session_roles, folder_roles, tag_roles


_library_store: InMemoryChatLibraryStore | None = None


def build_chat_library_store(database_url: str | None) -> ChatLibraryStore:
    global _library_store
    if database_url:
        return PostgresChatLibraryStore(database_url)
    if _library_store is None:
        _library_store = InMemoryChatLibraryStore()
    return _library_store

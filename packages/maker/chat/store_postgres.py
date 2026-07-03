from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

import psycopg
from psycopg.rows import dict_row

from iam.constants import DEFAULT_TENANT_ID
from maker.chat.library_models import AccessGrantRecord, FolderRecord, UserGroupRecord
from maker.chat.library_store import (
    _folder_from_row,
    _grant_from_row,
    _group_from_row,
    _utc_now,
    _validate_grant_inputs,
)


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
        _ = group_ids
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

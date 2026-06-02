from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

import psycopg
from psycopg.rows import dict_row

from nimbusware_iam.constants import DEFAULT_TENANT_ID
from nimbusware_maker.models import ATTACH_TEMPLATE, PROJECT_TEMPLATES, ProjectRecord


def _normalize_template(template: str) -> str:
    t = template.strip().lower()
    if t not in PROJECT_TEMPLATES:
        msg = f"invalid project template: {template!r}; expected one of {sorted(PROJECT_TEMPLATES)}"
        raise ValueError(msg)
    return t


def _resolve_workspace_path(raw: str) -> Path:
    path = Path(raw).expanduser().resolve()
    return path


def _row_to_record(row: dict[str, object]) -> ProjectRecord:
    return ProjectRecord(
        project_id=row["project_id"],  # type: ignore[arg-type]
        name=str(row["name"]),
        workspace_path=str(row["workspace_path"]),
        template=str(row["template"]),
        default_workflow_profile=str(row["default_workflow_profile"]),
        created_at=row["created_at"],  # type: ignore[arg-type]
        tenant_id=row["tenant_id"],  # type: ignore[arg-type]
    )


class InMemoryProjectStore:
    def __init__(self) -> None:
        self._projects: dict[UUID, ProjectRecord] = {}

    def create(
        self,
        *,
        name: str,
        workspace_path: str,
        template: str = ATTACH_TEMPLATE,
        default_workflow_profile: str = "micro_slice",
        tenant_id: UUID | None = None,
    ) -> ProjectRecord:
        name_n = name.strip()
        if not name_n:
            raise ValueError("project name required")
        template_n = _normalize_template(template)
        ws = _resolve_workspace_path(workspace_path)
        if template_n == "greenfield":
            ws.mkdir(parents=True, exist_ok=True)
        elif not ws.is_dir():
            raise ValueError(f"workspace_path is not a directory: {ws}")
        tid = tenant_id or DEFAULT_TENANT_ID
        pid = uuid4()
        row = ProjectRecord(
            project_id=pid,
            name=name_n,
            workspace_path=str(ws),
            template=template_n,
            default_workflow_profile=default_workflow_profile.strip() or "micro_slice",
            created_at=datetime.now(timezone.utc),
            tenant_id=tid,
        )
        self._projects[pid] = row
        return row

    def get(self, project_id: UUID) -> ProjectRecord | None:
        return self._projects.get(project_id)

    def list(self, *, tenant_id: UUID | None = None) -> list[ProjectRecord]:
        rows = list(self._projects.values())
        if tenant_id is not None:
            rows = [r for r in rows if r.tenant_id == tenant_id]
        return sorted(rows, key=lambda r: r.created_at, reverse=True)

    def update(
        self,
        project_id: UUID,
        *,
        name: str | None = None,
        workspace_path: str | None = None,
        default_workflow_profile: str | None = None,
    ) -> ProjectRecord:
        existing = self._projects.get(project_id)
        if existing is None:
            raise KeyError("project_not_found")
        name_n = name.strip() if name is not None else existing.name
        if not name_n:
            raise ValueError("project name required")
        ws_raw = workspace_path if workspace_path is not None else existing.workspace_path
        ws = _resolve_workspace_path(ws_raw)
        if existing.template == "attach" and not ws.is_dir():
            raise ValueError(f"workspace_path is not a directory: {ws}")
        profile = (
            default_workflow_profile.strip()
            if default_workflow_profile is not None
            else existing.default_workflow_profile
        )
        if not profile:
            raise ValueError("default_workflow_profile required")
        updated = ProjectRecord(
            project_id=existing.project_id,
            name=name_n,
            workspace_path=str(ws),
            template=existing.template,
            default_workflow_profile=profile,
            created_at=existing.created_at,
            tenant_id=existing.tenant_id,
        )
        self._projects[project_id] = updated
        return updated

    def delete(self, project_id: UUID) -> bool:
        return self._projects.pop(project_id, None) is not None


class PostgresProjectStore:
    def __init__(self, conninfo: str) -> None:
        self._conninfo = conninfo

    def create(
        self,
        *,
        name: str,
        workspace_path: str,
        template: str = ATTACH_TEMPLATE,
        default_workflow_profile: str = "micro_slice",
        tenant_id: UUID | None = None,
    ) -> ProjectRecord:
        name_n = name.strip()
        if not name_n:
            raise ValueError("project name required")
        template_n = _normalize_template(template)
        ws = _resolve_workspace_path(workspace_path)
        if template_n == "greenfield":
            ws.mkdir(parents=True, exist_ok=True)
        elif not ws.is_dir():
            raise ValueError(f"workspace_path is not a directory: {ws}")
        tid = tenant_id or DEFAULT_TENANT_ID
        pid = uuid4()
        with psycopg.connect(self._conninfo) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    INSERT INTO nimbusware_project (
                      project_id, tenant_id, name, workspace_path,
                      template, default_workflow_profile
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING project_id, tenant_id, name, workspace_path,
                              template, default_workflow_profile, created_at
                    """,
                    (
                        pid,
                        tid,
                        name_n,
                        str(ws),
                        template_n,
                        default_workflow_profile.strip() or "micro_slice",
                    ),
                )
                row = cur.fetchone()
            conn.commit()
        assert row is not None
        return _row_to_record(row)

    def get(self, project_id: UUID) -> ProjectRecord | None:
        with psycopg.connect(self._conninfo) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT project_id, tenant_id, name, workspace_path,
                           template, default_workflow_profile, created_at
                    FROM nimbusware_project
                    WHERE project_id = %s
                    """,
                    (project_id,),
                )
                row = cur.fetchone()
        if row is None:
            return None
        return _row_to_record(row)

    def list(self, *, tenant_id: UUID | None = None) -> list[ProjectRecord]:
        with psycopg.connect(self._conninfo) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                if tenant_id is None:
                    cur.execute(
                        """
                        SELECT project_id, tenant_id, name, workspace_path,
                               template, default_workflow_profile, created_at
                        FROM nimbusware_project
                        ORDER BY created_at DESC
                        """
                    )
                else:
                    cur.execute(
                        """
                        SELECT project_id, tenant_id, name, workspace_path,
                               template, default_workflow_profile, created_at
                        FROM nimbusware_project
                        WHERE tenant_id = %s
                        ORDER BY created_at DESC
                        """,
                        (tenant_id,),
                    )
                rows = cur.fetchall()
        return [_row_to_record(r) for r in rows]

    def update(
        self,
        project_id: UUID,
        *,
        name: str | None = None,
        workspace_path: str | None = None,
        default_workflow_profile: str | None = None,
    ) -> ProjectRecord:
        existing = self.get(project_id)
        if existing is None:
            raise KeyError("project_not_found")
        name_n = name.strip() if name is not None else existing.name
        if not name_n:
            raise ValueError("project name required")
        ws_raw = workspace_path if workspace_path is not None else existing.workspace_path
        ws = _resolve_workspace_path(ws_raw)
        if existing.template == "attach" and not ws.is_dir():
            raise ValueError(f"workspace_path is not a directory: {ws}")
        profile = (
            default_workflow_profile.strip()
            if default_workflow_profile is not None
            else existing.default_workflow_profile
        )
        if not profile:
            raise ValueError("default_workflow_profile required")
        with psycopg.connect(self._conninfo) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    UPDATE nimbusware_project
                    SET name = %s,
                        workspace_path = %s,
                        default_workflow_profile = %s
                    WHERE project_id = %s
                    RETURNING project_id, tenant_id, name, workspace_path,
                              template, default_workflow_profile, created_at
                    """,
                    (name_n, str(ws), profile, project_id),
                )
                row = cur.fetchone()
            conn.commit()
        assert row is not None
        return _row_to_record(row)

    def delete(self, project_id: UUID) -> bool:
        with psycopg.connect(self._conninfo) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM nimbusware_project WHERE project_id = %s",
                    (project_id,),
                )
                deleted = cur.rowcount > 0
            conn.commit()
        return deleted


def build_project_store(database_url: str | None) -> InMemoryProjectStore | PostgresProjectStore:
    if database_url:
        return PostgresProjectStore(database_url)
    return InMemoryProjectStore()

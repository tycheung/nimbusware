from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import HTTPException

from nimbusware_api.errors import problem
from nimbusware_env.edition import is_enterprise
from nimbusware_iam.context import get_auth_context, resolve_store_tenant_id
from nimbusware_maker.workspace import project_id_from_run_created_metadata


def _run_created_metadata(rows: list[dict[str, Any]]) -> dict[str, Any]:
    for row in rows:
        if row.get("event_type") == "run.created":
            meta = row.get("metadata")
            return dict(meta) if isinstance(meta, dict) else {}
    return {}


def assert_project_accessible(record: object, *, tenant_id: UUID | None = None) -> None:
    tid = tenant_id if tenant_id is not None else resolve_store_tenant_id()
    project_tid = getattr(record, "tenant_id", None)
    if project_tid is not None and UUID(str(project_tid)) != tid:
        raise HTTPException(
            status_code=404,
            detail=problem("project_not_found", "Unknown project id"),
        )


def assert_run_accessible(rows: list[dict[str, Any]], *, tenant_id: UUID | None = None) -> None:
    if not is_enterprise():
        return
    meta = _run_created_metadata(rows)
    pid = project_id_from_run_created_metadata(meta)
    if pid is None:
        return
    tid = tenant_id if tenant_id is not None else resolve_store_tenant_id()
    project = meta.get("project")
    if isinstance(project, dict):
        project_tid = project.get("tenant_id")
        if project_tid and UUID(str(project_tid)) != tid:
            raise HTTPException(
                status_code=404,
                detail=problem("run_not_found", "run not found"),
            )

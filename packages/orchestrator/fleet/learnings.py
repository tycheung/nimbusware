from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol
from uuid import UUID

from orchestrator.learnings_catalog import list_workspace_learnings


class TenantProjectStore(Protocol):
    def list(self, *, tenant_id: UUID | None = None) -> list[Any]: ...


def workspaces_for_tenant(project_store: TenantProjectStore, tenant_id: UUID) -> list[Path]:
    workspaces: list[Path] = []
    for project in project_store.list(tenant_id=tenant_id):
        raw = getattr(project, "workspace_path", None)
        if not isinstance(raw, str) or not raw.strip():
            continue
        path = Path(raw).expanduser().resolve()
        if path.is_dir():
            workspaces.append(path)
    return workspaces


def search_fleet_learnings(
    workspaces: list[Path],
    query: str,
    *,
    limit: int = 10,
) -> list[dict[str, Any]]:
    token = query.strip().lower()
    if not token:
        return []
    scored: list[tuple[int, dict[str, Any]]] = []
    for workspace in workspaces:
        for item in list_workspace_learnings(workspace, limit=50):
            haystack = f"{item.get('title', '')} {item.get('excerpt', '')}".lower()
            if token not in haystack:
                continue
            score = haystack.count(token)
            scored.append((score, {**item, "workspace": str(workspace)}))
    scored.sort(key=lambda row: (-row[0], str(row[1].get("title", ""))))
    cap = max(1, min(50, int(limit)))
    return [row for _, row in scored[:cap]]

from __future__ import annotations

from typing import Any
from uuid import UUID

from agent_core.mapping import mapping_or_empty
from nimbusware_orchestrator._pipeline._helpers import workflow_profile_from_run_created_rows


def optional_tri_allows_emit(tri: str | None) -> bool:
    return tri != "off"


def optional_rows_and_profile(host: Any, run_id: UUID) -> tuple[list[dict[str, Any]], str]:
    rows = host._store.list_run_events(str(run_id))
    wf = workflow_profile_from_run_created_rows(rows) or ""
    return rows, wf


def optional_meta_section(host: Any, run_id: UUID, key: str) -> dict[str, Any]:
    meta = host._run_created_metadata(run_id)
    return mapping_or_empty(meta.get(key))

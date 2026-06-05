"""Load event rows for memory index rebuild."""

from __future__ import annotations

import os
from typing import Any

import psycopg
from psycopg.rows import dict_row

from agent_core.models import EventType

_MEMORY_EVENT_TYPES = (
    EventType.RUN_CREATED.value,
    EventType.FINDING_CREATED.value,
    EventType.GATE_DECISION_EMITTED.value,
)


def fetch_event_rows_for_memory_index(
    *,
    conninfo: str | None = None,
    in_memory_rows: list[dict[str, Any]] | None = None,
    tenant_scoped: bool = False,
) -> list[dict[str, Any]]:
    """Return event rows needed for chunk extraction, ordered by ``store_seq``."""
    if in_memory_rows is not None:
        types = frozenset(_MEMORY_EVENT_TYPES)
        rows = [r for r in in_memory_rows if str(r.get("event_type")) in types]
        rows.sort(key=lambda r: int(r["store_seq"]))
        return rows
    url = (conninfo or os.environ.get("NIMBUSWARE_DATABASE_URL", "")).strip()
    if not url:
        msg = "NIMBUSWARE_DATABASE_URL is required to scan events for memory index"
        raise ValueError(msg)
    tenant_id = None
    if tenant_scoped:
        from nimbusware_iam.context import resolve_store_tenant_id

        tenant_id = str(resolve_store_tenant_id())
    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            if tenant_id is not None:
                cur.execute("SELECT set_config('nimbusware.tenant_id', %s, true)", (tenant_id,))
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT store_seq, event_id, run_id, event_type, payload, metadata
                FROM event_store
                WHERE event_type = ANY(%s)
                ORDER BY store_seq ASC
                """,
                (list(_MEMORY_EVENT_TYPES),),
            )
            return list(cur.fetchall())

"""pytest-benchmark helpers for fleet preflight aggregation."""

from __future__ import annotations

from typing import Any

from hermes_store.protocol import EventStore, serialized_event_from_row
from nimbusware_api.preflight_read_model import preflight_timeline_summary


def benchmark_preflight_history_scan(
    store: EventStore,
    *,
    limit: int = 50,
) -> dict[str, Any]:
    """Mirror hot path of ``GET /v1/preflight-history`` without HTTP."""
    ids = store.list_recent_run_ids(limit=limit, offset=0, order="newest_first")
    if hasattr(store, "list_run_events_many"):
        row_map = store.list_run_events_many([str(x) for x in ids])
    else:
        row_map = {str(x): store.list_run_events(str(x)) for x in ids}
    runs_with_preflight = 0
    p95_total = 0
    runs_with_p95 = 0
    for run_id in ids:
        rows = row_map.get(str(run_id), [])
        events = [serialized_event_from_row(r) for r in rows]
        pf = preflight_timeline_summary(events) if events else None
        if pf is not None:
            runs_with_preflight += 1
            p95 = pf.get("p95_latency_ms")
            if isinstance(p95, int) and not isinstance(p95, bool) and p95 >= 0:
                runs_with_p95 += 1
                p95_total += p95
    avg_p95 = (p95_total / runs_with_p95) if runs_with_p95 else None
    return {
        "runs_scanned": len(ids),
        "runs_with_preflight": runs_with_preflight,
        "avg_p95_latency_ms": avg_p95,
    }

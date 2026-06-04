from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from hermes_research.stitch_outcome_stats import (
    compute_stitch_transplant_stats,
    fetch_stitch_analytics_event_rows,
)
from nimbusware_api.deps import StoreDep

router = APIRouter(tags=["platform"])


@router.get("/platform/analytics/stitch-outcomes")
def get_platform_stitch_outcomes(
    store: StoreDep,
    limit_runs: int = Query(default=500, ge=1, le=5000),
) -> dict[str, Any]:
    rows = fetch_stitch_analytics_event_rows(store, limit_runs=limit_runs)
    stats = compute_stitch_transplant_stats(rows)
    return {
        **stats,
        "limit_runs": limit_runs,
        "runs_scanned": len({str(r.get("run_id")) for r in rows if r.get("run_id") is not None}),
    }

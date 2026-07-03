from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from api.deps import ChatStoreDep, OrchDep, StoreDep
from console.bundle_memory_display import (
    bundle_memory_analytics_from_store,
    bundle_memory_caption,
)
from env.dotenv import find_repo_root
from hw.pressure_history import pressure_history_from_event_rows
from projections.builders.chat_turn_analytics import build_chat_turn_summary
from projections.builders.competitive_metrics import build_competitive_summary
from research.stitch_outcome_stats import (
    compute_stitch_transplant_stats,
    fetch_stitch_analytics_event_rows,
)

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


@router.get("/platform/analytics/competitive-summary")
def get_platform_competitive_summary(
    store: StoreDep,
    limit_runs: int = Query(default=500, ge=1, le=5000),
) -> dict[str, Any]:
    return build_competitive_summary(
        store,
        limit_runs=limit_runs,
        repo_root=find_repo_root(),
    )


@router.get("/platform/analytics/pressure-history")
def get_platform_pressure_history(
    store: StoreDep,
    limit: int = Query(default=20, ge=1, le=200),
) -> dict[str, Any]:
    if not hasattr(store, "list_all_event_rows"):
        return {"limit": limit, "count": 0, "entries": []}
    rows = store.list_all_event_rows()
    history = pressure_history_from_event_rows(rows, limit=limit)
    return {"limit": limit, "count": len(history), "entries": history}


@router.get("/platform/analytics/chat-turns")
def get_platform_chat_turn_analytics(
    chat_store: ChatStoreDep,
    limit_sessions: int = Query(default=500, ge=1, le=5000),
) -> dict[str, Any]:
    if not hasattr(chat_store, "list_recent_analytics_turn_rows"):
        return build_chat_turn_summary([], limit_sessions=limit_sessions)
    rows = chat_store.list_recent_analytics_turn_rows(limit_sessions=limit_sessions)
    summary = build_chat_turn_summary(rows, limit_sessions=limit_sessions)
    from projections.builders.chat_journey_coverage import build_chat_journey_coverage

    summary["chat_journey_coverage"] = build_chat_journey_coverage(find_repo_root())
    return summary


@router.get("/platform/analytics/bundle-outcomes")
def get_platform_bundle_outcomes(orch: OrchDep) -> dict[str, Any]:
    store = getattr(orch, "_bundle_outcome_store", None)
    analytics = bundle_memory_analytics_from_store(store)
    return {
        "available": bool(analytics.get("available")),
        "outcome_count": int(analytics.get("outcome_count", 0)),
        "bundle_count": int(analytics.get("bundle_count", 0)),
        "caption": bundle_memory_caption(analytics),
        "rows": analytics.get("table_rows") or [],
    }

from __future__ import annotations

from typing import Any

from hermes_extensions.bundle_memory import BundleOutcomeStore, aggregate_bundle_success_stats
from hermes_extensions.bundle_memory_models import BundleSuccessStats


def bundle_success_stats_table_rows(
    stats: dict[str, BundleSuccessStats],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for bid in sorted(stats.keys()):
        stat = stats[bid]
        rows.append(
            {
                "bundle_id": stat.bundle_id,
                "pass_count": stat.pass_count,
                "fail_count": stat.fail_count,
                "sample_count": stat.sample_count,
                "success_rate": round(stat.success_rate, 3),
                "last_verdict": stat.last_verdict or "",
            },
        )
    rows.sort(key=lambda r: (-float(r["success_rate"]), -int(r["sample_count"]), str(r["bundle_id"])))
    return rows


def bundle_memory_analytics_from_store(
    store: BundleOutcomeStore | None,
) -> dict[str, Any]:
    if store is None:
        return {"available": False, "outcome_count": 0, "bundle_count": 0}
    records = store.list_all()
    stats = aggregate_bundle_success_stats(records)
    return {
        "available": True,
        "outcome_count": len(records),
        "bundle_count": len(stats),
        "stats": stats,
        "table_rows": bundle_success_stats_table_rows(stats),
    }


def bundle_memory_caption(analytics: dict[str, Any]) -> str:
    if not analytics.get("available"):
        return "Bundle memory unavailable (requires Postgres or in-memory store)."
    return (
        f"Bundle memory: **{analytics.get('outcome_count', 0)}** integrator outcomes across "
        f"**{analytics.get('bundle_count', 0)}** bundle ids."
    )

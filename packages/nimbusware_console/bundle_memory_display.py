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
                "avg_fit_score": (
                    round(stat.avg_integrator_score, 3)
                    if stat.avg_integrator_score is not None
                    else None
                ),
                "avg_fit_on_pass": (
                    round(stat.avg_score_on_pass, 3) if stat.avg_score_on_pass is not None else None
                ),
                "avg_fit_on_fail": (
                    round(stat.avg_score_on_fail, 3) if stat.avg_score_on_fail is not None else None
                ),
                "last_verdict": stat.last_verdict or "",
            },
        )
    rows.sort(
        key=lambda r: (-float(r["success_rate"]), -int(r["sample_count"]), str(r["bundle_id"]))
    )
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


def bundle_memory_fit_pass_caption(stats: dict[str, Any]) -> str | None:
    """One-line fit score vs gate pass correlation when scores exist."""
    scored = [
        s
        for s in stats.values()
        if getattr(s, "avg_score_on_pass", None) is not None
        or getattr(s, "avg_score_on_fail", None) is not None
    ]
    if not scored:
        return None
    parts: list[str] = []
    for stat in sorted(scored, key=lambda s: str(getattr(s, "bundle_id", "")))[:5]:
        bid = getattr(stat, "bundle_id", "?")
        on_pass = getattr(stat, "avg_score_on_pass", None)
        on_fail = getattr(stat, "avg_score_on_fail", None)
        rate = getattr(stat, "success_rate", None)
        if on_pass is not None and on_fail is not None:
            parts.append(f"`{bid}` pass {rate:.0%} (fit {on_pass:.2f} / {on_fail:.2f})")
        elif on_pass is not None:
            parts.append(f"`{bid}` pass {rate:.0%} (fit on pass {on_pass:.2f})")
        elif on_fail is not None:
            parts.append(f"`{bid}` pass {rate:.0%} (fit on fail {on_fail:.2f})")
    if not parts:
        return None
    return "Fit vs gate: " + "; ".join(parts)


def bundle_memory_caption(analytics: dict[str, Any]) -> str:
    if not analytics.get("available"):
        return "Bundle memory unavailable (requires Postgres or in-memory store)."
    base = (
        f"Bundle memory: **{analytics.get('outcome_count', 0)}** integrator outcomes across "
        f"**{analytics.get('bundle_count', 0)}** bundle ids."
    )
    stats = analytics.get("stats")
    if isinstance(stats, dict):
        fit_line = bundle_memory_fit_pass_caption(stats)
        if fit_line:
            return f"{base} {fit_line}"
    return base

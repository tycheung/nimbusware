from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from console.explainer_core.operator_metrics_exports import (
    install_operator_metrics_module,
)

_LINTER_EXIT_FIELDS: tuple[tuple[str, str], ...] = (
    ("Ruff", "security_scan_ruff_exit"),
    ("Bandit", "security_scan_bandit_exit"),
)


def security_scan_linter_status_rows(
    summary: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    if not isinstance(summary, Mapping):
        return []
    rows: list[dict[str, str]] = []
    for label, key in _LINTER_EXIT_FIELDS:
        raw = summary.get(key)
        if isinstance(raw, bool) or not isinstance(raw, int):
            rows.append({"linter": label, "exit": "—", "status": "missing"})
            continue
        rows.append(
            {
                "linter": label,
                "exit": str(raw),
                "status": "ok" if raw == 0 else "failed",
            },
        )
    return rows


def security_scan_linter_status_summary_caption(
    summary: Mapping[str, Any] | None,
) -> str | None:
    rows = security_scan_linter_status_rows(summary)
    if not rows:
        return None
    tallies = {"ok": 0, "failed": 0, "missing": 0}
    for row in rows:
        status = row.get("status")
        if status in tallies:
            tallies[status] += 1
    if tallies["ok"] == 0 and tallies["failed"] == 0:
        return None
    return (
        "Linter summary: "
        f"{tallies['ok']} ok, "
        f"{tallies['failed']} failed, "
        f"{tallies['missing']} missing."
    )


def security_scan_linter_worst_status_caption(
    summary: Mapping[str, Any] | None,
) -> str | None:
    rows = security_scan_linter_status_rows(summary)
    if not rows:
        return None
    failed = [r for r in rows if r.get("status") == "failed"]
    if failed:
        first = failed[0]
        return f"Worst linter: **{first['linter']}** (exit `{first['exit']}`)."
    ok_rows = [r for r in rows if r.get("status") == "ok"]
    if not ok_rows:
        return None
    parts = ", ".join(f"{r['linter']} exit {r['exit']}" for r in ok_rows)
    return f"All linters passed ({parts})."


def security_scan_linter_operator_metrics(
    summary: Mapping[str, Any] | None,
) -> dict[str, Any]:
    metrics: dict[str, Any] = {
        "observable_count": 0,
        "ok_count": 0,
        "failed_count": 0,
        "missing_count": 0,
        "worst_status": None,
        "worst_linter": None,
        "worst_exit": None,
    }
    rows = security_scan_linter_status_rows(summary)
    if not rows:
        return metrics
    failed_row: dict[str, str] | None = None
    for row in rows:
        status = row.get("status")
        if status == "ok":
            metrics["ok_count"] += 1
        elif status == "failed":
            metrics["failed_count"] += 1
            if failed_row is None:
                failed_row = row
        else:
            metrics["missing_count"] += 1
    metrics["observable_count"] = metrics["ok_count"] + metrics["failed_count"]
    if failed_row is not None:
        metrics["worst_status"] = "failed"
        metrics["worst_linter"] = failed_row["linter"]
        try:
            metrics["worst_exit"] = int(failed_row["exit"])
        except (TypeError, ValueError):
            metrics["worst_exit"] = None
    elif metrics["ok_count"] > 0:
        metrics["worst_status"] = "ok"
    return metrics


def security_scan_linter_operator_metrics_caption(
    metrics: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(metrics, Mapping):
        return None
    if metrics.get("observable_count", 0) == 0:
        return None
    parts = [
        f"observable={metrics['observable_count']}",
        f"ok={metrics.get('ok_count', 0)}",
        f"failed={metrics.get('failed_count', 0)}",
        f"missing={metrics.get('missing_count', 0)}",
    ]
    worst = metrics.get("worst_status")
    if worst == "failed":
        wl = metrics.get("worst_linter")
        we = metrics.get("worst_exit")
        if wl is not None and we is not None:
            parts.append(f"worst={wl} exit {we}")
        else:
            parts.append("worst=failed")
    elif worst == "ok":
        parts.append("worst=all ok")
    return "Linter operator metrics: " + ", ".join(parts) + "."


def security_scan_linter_operator_rollup_caption(
    summary: Mapping[str, Any] | None,
) -> str | None:
    return security_scan_linter_operator_metrics_caption(
        security_scan_linter_operator_metrics(summary),
    )


def security_scan_linter_ok_linters_caption(
    summary: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(summary, Mapping):
        return None
    passing: list[str] = []
    for label, key in _LINTER_EXIT_FIELDS:
        raw = summary.get(key)
        if isinstance(raw, bool) or not isinstance(raw, int):
            continue
        if raw == 0:
            passing.append(label)
    if not passing:
        return None
    if len(passing) == 1:
        return f"Passing linter: {passing[0]}."
    return "Passing linters: " + ", ".join(passing) + "."


def security_scan_linter_missing_linters_caption(
    summary: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(summary, Mapping):
        return None
    missing: list[str] = []
    for label, key in _LINTER_EXIT_FIELDS:
        raw = summary.get(key)
        if isinstance(raw, bool) or not isinstance(raw, int):
            missing.append(label)
    if not missing:
        return None
    if len(missing) == 1:
        return f"Missing linter: {missing[0]}."
    return "Missing linters: " + ", ".join(missing) + "."


def security_scan_linter_failed_linters_caption(
    summary: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(summary, Mapping):
        return None
    failed: list[str] = []
    for label, key in _LINTER_EXIT_FIELDS:
        raw = summary.get(key)
        if isinstance(raw, bool) or not isinstance(raw, int):
            continue
        if raw != 0:
            failed.append(label)
    if not failed:
        return None
    if len(failed) == 1:
        return f"Failed linter: {failed[0]}."
    return "Failed linters: " + ", ".join(failed) + "."


def security_scan_linter_exit_codes_caption(
    summary: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(summary, Mapping):
        return None
    observed: list[str] = []
    for label, key in _LINTER_EXIT_FIELDS:
        raw = summary.get(key)
        if isinstance(raw, bool) or not isinstance(raw, int):
            continue
        observed.append(f"{label}={raw}")
    if not observed:
        return None
    return "Linter exit codes: " + ", ".join(observed) + "."


def security_scan_linter_operator_metrics_table_rows(
    metrics: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    if not isinstance(metrics, Mapping) or not metrics:
        return []
    rows: list[dict[str, str]] = [
        {"field": "Observable linters", "value": str(metrics.get("observable_count", 0))},
        {"field": "Ok", "value": str(metrics.get("ok_count", 0))},
        {"field": "Failed", "value": str(metrics.get("failed_count", 0))},
        {"field": "Missing", "value": str(metrics.get("missing_count", 0))},
    ]
    worst_status = metrics.get("worst_status")
    if worst_status is None:
        return rows
    rows.append({"field": "Worst status", "value": str(worst_status)})
    worst_linter = metrics.get("worst_linter")
    if worst_linter is not None:
        rows.append({"field": "Worst linter", "value": str(worst_linter)})
    worst_exit = metrics.get("worst_exit")
    if worst_exit is not None:
        rows.append({"field": "Worst exit", "value": str(worst_exit)})
    return rows


(
    security_scan_linter_operator_metrics,
    security_scan_linter_operator_metrics_table_rows,
    security_scan_linter_operator_metrics_caption,
    security_scan_linter_operator_metrics_export_json,
    security_scan_linter_operator_metrics_table_rows_csv,
    _security_scan_linter_operator_metrics_exports_slug,
) = install_operator_metrics_module(
    globals(),
    module_prefix="security_scan_linter",
    metrics=security_scan_linter_operator_metrics,
    table_rows=security_scan_linter_operator_metrics_table_rows,
    caption=security_scan_linter_operator_metrics_caption,
    export_slug="security_scan_linter_operator_metrics",
)

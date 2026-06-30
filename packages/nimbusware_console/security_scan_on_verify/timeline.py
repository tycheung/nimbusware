from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from functools import partial
from typing import Any

from agent_core.coercion import is_strict_int
from nimbusware_console.components.operator_metrics import table_rows_csv
from nimbusware_console.explainer_core.display_common import stringify_display_value as _stringify
from nimbusware_console.explainer_core.operator_metrics_exports import (
    install_operator_metrics_module,
)
from nimbusware_console.explainer_core.workflow_exports import run_id_export_filename_slug


def security_scan_on_verify_from_timeline(
    timeline_body: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(timeline_body, Mapping):
        return None
    raw = timeline_body.get("security_scan_on_verify")
    return raw if isinstance(raw, dict) else None


def security_scan_history_from_timeline(
    timeline_body: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    if not isinstance(timeline_body, Mapping):
        return []
    raw = timeline_body.get("security_scan_on_verify_history")
    if not isinstance(raw, list):
        return []
    return [x for x in raw if isinstance(x, dict)]


def security_scan_history_table_rows(
    history: list[dict[str, Any]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for i, e in enumerate(history, start=1):
        rows.append(
            {
                "#": str(i),
                "Occurred at": _stringify(e.get("occurred_at")),
                "Severity": _stringify(e.get("severity")),
                "Ruff exit": _stringify(e.get("security_scan_ruff_exit")),
                "Bandit exit": _stringify(e.get("security_scan_bandit_exit")),
                "Scan exit": _stringify(e.get("security_scan_exit")),
                "Finding id": _stringify(e.get("finding_id")),
                "Event id": _stringify(e.get("event_id")),
            },
        )
    return rows


_SECURITY_SCAN_HISTORY_CSV_COLUMNS: tuple[str, ...] = (
    "#",
    "Occurred at",
    "Severity",
    "Ruff exit",
    "Bandit exit",
    "Scan exit",
    "Finding id",
    "Event id",
)


security_scan_history_table_rows_csv = partial(
    table_rows_csv,
    columns=_SECURITY_SCAN_HISTORY_CSV_COLUMNS,
)


def security_scan_history_export_json(history: Sequence[Mapping[str, Any]]) -> str:
    items = [dict(x) for x in history if isinstance(x, Mapping)]
    return json.dumps(items, ensure_ascii=False, indent=2)


def security_scan_history_export_filename_slug(run_id: str, *, max_len: int = 36) -> str:
    return run_id_export_filename_slug(run_id, max_len=max_len)


def security_scan_history_entry_count_caption(
    history: list[dict[str, Any]] | None,
) -> str | None:
    if not history:
        return None
    n = len(history)
    word = "finding" if n == 1 else "findings"
    return f"Security scan history: **{n}** {word} in this timeline view."


def security_scan_history_severity_sample_caption(
    history: list[dict[str, Any]] | None,
    *,
    max_n: int = 6,
) -> str | None:
    if not history or max_n <= 0:
        return None
    severities: set[str] = set()
    for entry in history:
        if not isinstance(entry, dict):
            continue
        sev = entry.get("severity")
        if isinstance(sev, str) and sev.strip():
            severities.add(sev.strip())
    if not severities:
        return None
    ordered = sorted(severities)
    cap = max(1, int(max_n))
    visible = ordered[:cap]
    overflow = len(ordered) - len(visible)
    inner = ", ".join(visible)
    if overflow > 0:
        inner += f" (+{overflow} more)"
    word = "severity" if len(ordered) == 1 else "severities"
    return f"Security scan history distinct {word}: {inner}."


def security_scan_history_operator_metrics(
    history: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    metrics: dict[str, Any] = {
        "entry_count": 0,
        "distinct_severity_count": 0,
        "severity_sample": [],
        "ruff_nonzero_exit_count": 0,
        "bandit_nonzero_exit_count": 0,
        "failed_scan_exit_count": 0,
    }
    if not history:
        return metrics
    severities: set[str] = set()
    for entry in history:
        if not isinstance(entry, dict):
            continue
        metrics["entry_count"] = int(metrics["entry_count"]) + 1
        sev = entry.get("severity")
        if isinstance(sev, str) and sev.strip():
            severities.add(sev.strip())
        for field, key in (
            ("security_scan_ruff_exit", "ruff_nonzero_exit_count"),
            ("security_scan_bandit_exit", "bandit_nonzero_exit_count"),
            ("security_scan_exit", "failed_scan_exit_count"),
        ):
            val = entry.get(field)
            if is_strict_int(val) and val != 0:
                metrics[key] = int(metrics[key]) + 1
    metrics["distinct_severity_count"] = len(severities)
    metrics["severity_sample"] = sorted(severities)[:5]
    return metrics


def security_scan_history_operator_metrics_table_rows(
    metrics: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    if not isinstance(metrics, Mapping):
        return []
    rows: list[dict[str, str]] = [
        {"field": "Entry count", "value": str(metrics.get("entry_count", 0))},
        {
            "field": "Distinct severities",
            "value": str(metrics.get("distinct_severity_count", 0)),
        },
    ]
    sample = metrics.get("severity_sample")
    if isinstance(sample, list) and sample:
        rows.append(
            {
                "field": "Severity sample",
                "value": ", ".join(str(x) for x in sample if isinstance(x, str)),
            },
        )
    for key, label in (
        ("ruff_nonzero_exit_count", "Ruff non-zero exits"),
        ("bandit_nonzero_exit_count", "Bandit non-zero exits"),
        ("failed_scan_exit_count", "Scan non-zero exits"),
    ):
        n = metrics.get(key, 0)
        if is_strict_int(n) and n > 0:
            rows.append({"field": label, "value": str(n)})
    return rows


def security_scan_history_operator_metrics_caption(
    metrics: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(metrics, Mapping):
        return None
    ec = metrics.get("entry_count")
    if isinstance(ec, bool) or not isinstance(ec, int) or ec < 1:
        return None
    parts = [f"**{ec}** finding(s)"]
    dsc = metrics.get("distinct_severity_count", 0)
    if is_strict_int(dsc) and dsc > 0:
        parts.append(f"**{dsc}** distinct severity")
    sample = metrics.get("severity_sample")
    if isinstance(sample, list) and sample:
        visible = [str(x) for x in sample[:3] if isinstance(x, str) and str(x).strip()]
        if visible:
            inner = ", ".join(visible)
            overflow = len(sample) - len(visible)
            if overflow > 0:
                inner += f" (+{overflow} more)"
            parts.append(f"severity sample: {inner}")
    for key, label in (
        ("ruff_nonzero_exit_count", "Ruff failed"),
        ("bandit_nonzero_exit_count", "Bandit failed"),
        ("failed_scan_exit_count", "Scan failed"),
    ):
        n = metrics.get(key, 0)
        if is_strict_int(n) and n > 0:
            parts.append(f"**{n}** {label}")
    return "Security scan history metrics: " + ", ".join(parts) + "."


(
    security_scan_history_operator_metrics,
    security_scan_history_operator_metrics_table_rows,
    security_scan_history_operator_metrics_caption,
    security_scan_history_operator_metrics_export_json,
    security_scan_history_operator_metrics_table_rows_csv,
    _security_scan_history_operator_metrics_exports_slug,
) = install_operator_metrics_module(
    globals(),
    module_prefix="security_scan_history",
    metrics=security_scan_history_operator_metrics,
    table_rows=security_scan_history_operator_metrics_table_rows,
    caption=security_scan_history_operator_metrics_caption,
    export_slug="security_scan_history_operator_metrics",
)


def security_scan_history_operator_metrics_export_filename_slug(
    run_id: str,
    *,
    max_len: int = 36,
) -> str:
    return security_scan_history_export_filename_slug(run_id, max_len=max_len)

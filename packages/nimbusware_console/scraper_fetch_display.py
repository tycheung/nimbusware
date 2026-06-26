from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from functools import partial
from typing import Any

from agent_core.coercion import is_strict_int
from nimbusware_console.components.operator_metrics import (
    mapping_export_json,
    sequence_export_json,
    table_rows_csv,
)
from nimbusware_console.explainer_core.operator_metrics_exports import bind_operator_metrics_exports
from nimbusware_console.explainer_core.table_rows_csv import field_value_table_rows_csv
from nimbusware_console.explainer_core.workflow_exports import run_id_export_filename_slug

_SCRAPER_FETCH_FIELDS: tuple[tuple[str, str], ...] = (
    ("outcome", "Outcome"),
    ("fetch_count", "Fetch count"),
    ("total_bytes", "Total bytes"),
    ("reason_code", "Reason code"),
    ("failed_url_host", "Failed URL host"),
    ("message", "Message"),
    ("stage_name", "Stage name"),
    ("event_id", "Event id"),
    ("occurred_at", "Occurred at"),
)


def _stringify(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def scraper_fetch_from_timeline(
    timeline_body: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(timeline_body, Mapping):
        return None
    raw = timeline_body.get("scraper_fetch")
    return raw if isinstance(raw, dict) else None


def scraper_fetch_summary_rows(
    summary: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    if not summary:
        return []
    rows: list[dict[str, str]] = []
    for key, label in _SCRAPER_FETCH_FIELDS:
        if key not in summary:
            continue
        rows.append({"field": label, "value": _stringify(summary.get(key))})
    return rows


_SCRAPER_FETCH_SUMMARY_CSV_COLUMNS: tuple[str, ...] = ("field", "value")


scraper_fetch_summary_rows_csv = field_value_table_rows_csv


def scraper_fetch_summary_export_json(summary: Mapping[str, Any] | None) -> str:
    return mapping_export_json(summary)


def scraper_fetch_summary_export_filename_slug(run_id: str, *, max_len: int = 36) -> str:
    return run_id_export_filename_slug(run_id, max_len=max_len)


def scraper_fetch_outcome_caption(summary: Mapping[str, Any] | None) -> str | None:
    if not isinstance(summary, Mapping):
        return None
    outcome = summary.get("outcome")
    if not isinstance(outcome, str) or not outcome.strip():
        return None
    fc = summary.get("fetch_count")
    tb = summary.get("total_bytes")
    parts = [f"Scraper fetch: {outcome.strip()}."]
    if is_strict_int(fc):
        parts.append(f" {fc} URL(s)")
        if is_strict_int(tb):
            parts.append(f", {tb} bytes total.")
        else:
            parts.append(".")
    return "".join(parts)


def scraper_fetch_fetches_table_rows(
    summary: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    if not isinstance(summary, Mapping):
        return []
    raw = summary.get("fetches")
    if not isinstance(raw, list):
        return []
    rows: list[dict[str, str]] = []
    for i, row in enumerate(raw, start=1):
        if not isinstance(row, dict):
            continue
        rows.append(
            {
                "#": str(i),
                "URL host": _stringify(row.get("url_host")),
                "HTTP status": _stringify(row.get("http_status")),
                "Bytes": _stringify(row.get("bytes")),
                "Attempts": _stringify(row.get("attempts")),
                "Content length": _stringify(row.get("content_length")),
                "Artifact relpath": _stringify(row.get("artifact_relpath")),
            },
        )
    return rows


_SCRAPER_FETCH_FETCHES_CSV_COLUMNS: tuple[str, ...] = (
    "#",
    "URL host",
    "HTTP status",
    "Bytes",
    "Attempts",
    "Content length",
    "Artifact relpath",
)


scraper_fetch_fetches_table_rows_csv = partial(
    table_rows_csv,
    columns=_SCRAPER_FETCH_FETCHES_CSV_COLUMNS,
)


def scraper_fetch_fetches_export_json(summary: Mapping[str, Any] | None) -> str:
    if not isinstance(summary, Mapping):
        return "[]"
    raw = summary.get("fetches")
    if not isinstance(raw, list):
        return "[]"
    return sequence_export_json([dict(x) for x in raw if isinstance(x, dict)])


def scraper_fetch_fetches_export_filename_slug(run_id: str, *, max_len: int = 36) -> str:
    return scraper_fetch_summary_export_filename_slug(run_id, max_len=max_len)


def scraper_fetch_artifacts_caption(summary: Mapping[str, Any] | None) -> str | None:
    if not isinstance(summary, Mapping):
        return None
    raw = summary.get("fetches")
    if not isinstance(raw, list) or not raw:
        return None
    n = sum(
        1
        for row in raw
        if isinstance(row, dict)
        and isinstance(row.get("artifact_relpath"), str)
        and str(row["artifact_relpath"]).strip()
    )
    if n == 0:
        return None
    word = "row" if n == 1 else "rows"
    return f"Scraper fetch artifacts: **{n}** per-URL {word} with artifact_relpath."


def scraper_fetch_failure_reason_caption(summary: Mapping[str, Any] | None) -> str | None:
    if not isinstance(summary, Mapping):
        return None
    if summary.get("outcome") != "failed":
        return None
    rc = summary.get("reason_code")
    if not isinstance(rc, str) or not rc.strip():
        return None
    host = summary.get("failed_url_host")
    if isinstance(host, str) and host.strip():
        return f"Failure reason: {rc.strip()} (host {host.strip()})."
    return f"Failure reason: {rc.strip()}."


def _scraper_fetch_artifact_relpath_count(summary: Mapping[str, Any]) -> int:
    raw = summary.get("fetches")
    if not isinstance(raw, list):
        return 0
    return sum(
        1
        for row in raw
        if isinstance(row, dict)
        and isinstance(row.get("artifact_relpath"), str)
        and str(row["artifact_relpath"]).strip()
    )


def scraper_fetch_operator_metrics(
    summary: Mapping[str, Any] | None,
) -> dict[str, Any]:
    metrics: dict[str, Any] = {
        "outcome": None,
        "fetch_count": 0,
        "total_bytes": 0,
        "artifact_relpath_count": 0,
        "failed_url_present": False,
    }
    if not isinstance(summary, Mapping):
        return metrics
    outcome = summary.get("outcome")
    if isinstance(outcome, str) and outcome.strip():
        metrics["outcome"] = outcome.strip()
    fc = summary.get("fetch_count")
    if is_strict_int(fc):
        metrics["fetch_count"] = fc
    tb = summary.get("total_bytes")
    if is_strict_int(tb):
        metrics["total_bytes"] = tb
    metrics["artifact_relpath_count"] = _scraper_fetch_artifact_relpath_count(summary)
    host = summary.get("failed_url_host")
    metrics["failed_url_present"] = isinstance(host, str) and bool(host.strip())
    return metrics


def scraper_fetch_operator_metrics_table_rows(
    metrics: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    if not isinstance(metrics, Mapping):
        return []
    rows: list[dict[str, str]] = []
    outcome = metrics.get("outcome")
    if isinstance(outcome, str) and outcome.strip():
        rows.append({"field": "Outcome", "value": outcome.strip()})
    rows.append({"field": "Fetch count", "value": str(metrics.get("fetch_count", 0))})
    rows.append({"field": "Total bytes", "value": str(metrics.get("total_bytes", 0))})
    arc = metrics.get("artifact_relpath_count", 0)
    if is_strict_int(arc) and arc > 0:
        rows.append({"field": "Artifact relpath rows", "value": str(arc)})
    if metrics.get("failed_url_present") is True:
        rows.append({"field": "Failed URL host present", "value": "yes"})
    return rows


def scraper_fetch_operator_metrics_caption(
    metrics: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(metrics, Mapping):
        return None
    outcome = metrics.get("outcome")
    if not isinstance(outcome, str) or not outcome.strip():
        return None
    parts = [f"**{outcome.strip()}**"]
    fc = metrics.get("fetch_count", 0)
    if is_strict_int(fc) and fc > 0:
        parts.append(f"**{fc}** URL(s)")
    tb = metrics.get("total_bytes", 0)
    if is_strict_int(tb) and tb > 0:
        parts.append(f"**{tb}** bytes")
    arc = metrics.get("artifact_relpath_count", 0)
    if is_strict_int(arc) and arc > 0:
        parts.append(f"**{arc}** artifact row(s)")
    return "Scraper fetch metrics: " + ", ".join(parts) + "."


(
    scraper_fetch_operator_metrics_export_json,
    scraper_fetch_operator_metrics_table_rows_csv,
    _scraper_fetch_operator_metrics_exports_slug,
) = bind_operator_metrics_exports(export_slug="scraper_fetch_operator_metrics")


def scraper_fetch_operator_metrics_export_filename_slug(
    run_id: str,
    *,
    max_len: int = 36,
) -> str:
    return scraper_fetch_summary_export_filename_slug(run_id, max_len=max_len)

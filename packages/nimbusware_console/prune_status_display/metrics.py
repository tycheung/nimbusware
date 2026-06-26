from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

from agent_core.coercion import is_strict_int

SCRAPER_ARTIFACT_PRUNE_WORKFLOW_RELPATH = ".github/workflows/scraper_artifact_prune.yml"

from nimbusware_console.explainer_core.operator_metrics_exports import install_operator_metrics_module
from nimbusware_console.prune_status_display.status_captions import (
    _parse_wrote_at,
)


def _prune_status_is_stale(
    status: Mapping[str, Any] | None,
    *,
    now: datetime | None = None,
    stale_after_hours: int = 24,
) -> bool:
    if not isinstance(status, Mapping):
        return False
    wrote_at = _parse_wrote_at(status.get("wrote_at"))
    if wrote_at is None:
        return False
    if wrote_at.tzinfo is None:
        wrote_at = wrote_at.replace(tzinfo=timezone.utc)
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    delta = current - wrote_at
    return int(delta.total_seconds()) > stale_after_hours * 3600


def _prune_status_pattern_count(status: Mapping[str, Any], field: str) -> int:
    raw = status.get(field)
    if is_strict_int(raw):
        return raw
    raw_list = status.get(
        "include_patterns" if field == "include_pattern_count" else "exclude_patterns",
    )
    if isinstance(raw_list, list):
        return len(raw_list)
    return 0


def prune_status_operator_metrics(
    status: Mapping[str, Any] | None,
    *,
    now: datetime | None = None,
    stale_after_hours: int = 24,
) -> dict[str, Any]:
    metrics: dict[str, Any] = {
        "pruned": None,
        "dry_run": None,
        "max_age_days": None,
        "include_pattern_count": 0,
        "exclude_pattern_count": 0,
        "schema_version": None,
        "is_stale": False,
        "retention_alert_level": None,
        "retention_stale_file_count": None,
        "retention_stale_bytes": None,
        "retention_lifecycle_state": None,
    }
    if not isinstance(status, Mapping):
        return metrics
    pruned = status.get("pruned")
    if is_strict_int(pruned) and pruned >= 0:
        metrics["pruned"] = pruned
    dry = status.get("dry_run")
    if isinstance(dry, bool):
        metrics["dry_run"] = dry
    max_age = status.get("max_age_days")
    if is_strict_int(max_age) and max_age >= 1:
        metrics["max_age_days"] = max_age
    metrics["include_pattern_count"] = _prune_status_pattern_count(
        status,
        "include_pattern_count",
    )
    metrics["exclude_pattern_count"] = _prune_status_pattern_count(
        status,
        "exclude_pattern_count",
    )
    schema = status.get("schema_version")
    if is_strict_int(schema) and schema > 0:
        metrics["schema_version"] = schema
    metrics["is_stale"] = _prune_status_is_stale(
        status,
        now=now,
        stale_after_hours=stale_after_hours,
    )
    alert_level = status.get("retention_alert_level")
    if isinstance(alert_level, str) and alert_level.strip():
        metrics["retention_alert_level"] = alert_level.strip()
    stale_n = status.get("retention_stale_file_count")
    if is_strict_int(stale_n) and stale_n >= 0:
        metrics["retention_stale_file_count"] = stale_n
    stale_b = status.get("retention_stale_bytes")
    if is_strict_int(stale_b) and stale_b >= 0:
        metrics["retention_stale_bytes"] = stale_b
    lifecycle = status.get("retention_lifecycle_state")
    if isinstance(lifecycle, str) and lifecycle.strip():
        metrics["retention_lifecycle_state"] = lifecycle.strip()
    return metrics


def prune_status_operator_metrics_table_rows(
    metrics: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    if not isinstance(metrics, Mapping):
        return []
    rows: list[dict[str, str]] = []
    pruned = metrics.get("pruned")
    if is_strict_int(pruned):
        rows.append({"field": "Pruned paths", "value": str(pruned)})
    dry = metrics.get("dry_run")
    if isinstance(dry, bool):
        rows.append({"field": "Dry run", "value": str(dry).lower()})
    max_age = metrics.get("max_age_days")
    if is_strict_int(max_age):
        rows.append({"field": "Max age (days)", "value": str(max_age)})
    inc = metrics.get("include_pattern_count", 0)
    if is_strict_int(inc) and inc > 0:
        rows.append({"field": "Include patterns", "value": str(inc)})
    exc = metrics.get("exclude_pattern_count", 0)
    if is_strict_int(exc) and exc > 0:
        rows.append({"field": "Exclude patterns", "value": str(exc)})
    schema = metrics.get("schema_version")
    if is_strict_int(schema):
        rows.append({"field": "Schema version", "value": str(schema)})
    if metrics.get("is_stale") is True:
        rows.append({"field": "Stale (>24h)", "value": "yes"})
    alert_level = metrics.get("retention_alert_level")
    if isinstance(alert_level, str) and alert_level.strip() and alert_level.strip() != "none":
        rows.append({"field": "Retention alert level", "value": alert_level.strip()})
    stale_n = metrics.get("retention_stale_file_count")
    if is_strict_int(stale_n):
        rows.append({"field": "Retention stale files", "value": str(stale_n)})
    stale_b = metrics.get("retention_stale_bytes")
    if is_strict_int(stale_b):
        rows.append({"field": "Retention stale bytes", "value": str(stale_b)})
    lifecycle = metrics.get("retention_lifecycle_state")
    if isinstance(lifecycle, str) and lifecycle.strip():
        rows.append({"field": "Retention lifecycle", "value": lifecycle.strip()})
    return rows


def prune_status_operator_metrics_caption(
    metrics: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(metrics, Mapping):
        return None
    pruned = metrics.get("pruned")
    if not isinstance(pruned, int) or isinstance(pruned, bool):
        return None
    parts = [f"**{pruned}** path(s) pruned"]
    dry = metrics.get("dry_run")
    if dry is True:
        parts.append("dry run")
    elif dry is False:
        parts.append("live run")
    if metrics.get("is_stale") is True:
        parts.append("stale status")
    alert_level = metrics.get("retention_alert_level")
    if isinstance(alert_level, str) and alert_level.strip() and alert_level.strip() != "none":
        parts.append(f"retention_alert={alert_level.strip()}")
    lifecycle = metrics.get("retention_lifecycle_state")
    if isinstance(lifecycle, str) and lifecycle.strip():
        parts.append(f"lifecycle={lifecycle.strip()}")
    return "Prune status metrics: " + ", ".join(parts) + "."


(
    prune_status_operator_metrics,
    prune_status_operator_metrics_table_rows,
    prune_status_operator_metrics_caption,
    prune_status_operator_metrics_export_json,
    prune_status_operator_metrics_table_rows_csv,
    prune_status_operator_metrics_export_filename_slug,
) = install_operator_metrics_module(
    globals(),
    module_prefix="prune_status",
    metrics=prune_status_operator_metrics,
    table_rows=prune_status_operator_metrics_table_rows,
    caption=prune_status_operator_metrics_caption,
    export_slug="prune_status_operator_metrics",
)

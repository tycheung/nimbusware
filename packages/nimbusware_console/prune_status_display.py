"""Prune status card helpers for Streamlit (plan §14 #11.

Bridges the JSON state file written by ``scripts/prune_scraper_artifacts.py``
(``--summary-path`` / ``HERMES_PRUNE_STATUS_PATH``) to the Streamlit console.
Three pure functions so they can be unit-tested without spinning up Streamlit:

* :func:`load_prune_status` — defensively read the state file (never raises).
* :func:`prune_status_summary_rows` — field/value rows for ``st.dataframe``.
* :func:`prune_status_freshness_caption` — operator-readable freshness blurb.
"""

from __future__ import annotations

import csv
import json
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from typing import Any

SCRAPER_ARTIFACT_PRUNE_WORKFLOW_RELPATH = (
    ".github/workflows/scraper_artifact_prune.yml"
)


def prune_scraper_artifact_prune_workflow_caption() -> str:
    """One-line pointer to the scheduled prune GitHub Actions workflow."""
    return (
        f"Scheduled prune workflow: ``{SCRAPER_ARTIFACT_PRUNE_WORKFLOW_RELPATH}`` "
        "(cron / workflow_dispatch; not default CI)."
    )


def prune_status_schema_version_caption(
    status: Mapping[str, Any] | None,
) -> str | None:
    """One-line ``schema_version`` from the prune JSON summary."""
    if not isinstance(status, Mapping):
        return None
    raw = status.get("schema_version")
    if not isinstance(raw, int) or isinstance(raw, bool) or raw <= 0:
        return None
    return f"Prune status schema_version: **{raw}**."


_PRUNE_STATUS_FIELDS: tuple[tuple[str, str], ...] = (
    ("schema_version", "Summary schema version"),
    ("pruned", "Pruned"),
    ("base", "Base dir"),
    ("dry_run", "Dry run"),
    ("max_age_days", "Max age (days)"),
    ("include_patterns", "Include patterns"),
    ("exclude_patterns", "Exclude patterns"),
    ("include_pattern_count", "Include pattern count"),
    ("exclude_pattern_count", "Exclude pattern count"),
    ("wrote_at", "Wrote at (UTC)"),
)


def _stringify(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def load_prune_status(path: Path | None) -> dict[str, Any] | None:
    """Read ``path`` as JSON. Returns ``None`` on any failure (never raises).

    Defensive in five ways so the console expander can call this unconditionally:

    * ``path is None`` ⇒ ``None`` (env not set).
    * File missing ⇒ ``None`` (operator hasn't run the prune script yet).
    * ``OSError`` on read ⇒ ``None`` (permission / locking issue).
    * JSON decode error ⇒ ``None`` (partial write / hand-edit gone wrong).
    * Top-level not a dict ⇒ ``None`` (someone wrote a list / scalar).
    """
    if path is None:
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def prune_status_summary_rows(
    status: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    """Rows for ``st.dataframe`` (field / value columns).

    Returns ``[]`` when ``status`` is falsy so the caller can show a neutral
    caption instead of an empty table. Renders ``None`` values as ``—`` (same
    em-dash convention used by ``preflight_history_summary_rows``).
    """
    if not status:
        return []
    rows: list[dict[str, str]] = []
    for key, label in _PRUNE_STATUS_FIELDS:
        if key not in status:
            continue
        rows.append({"field": label, "value": _stringify(status.get(key))})
    return rows


_PRUNE_STATUS_SUMMARY_CSV_COLUMNS: tuple[str, ...] = ("field", "value")


def prune_status_export_json(status: Mapping[str, Any] | None) -> str:
    """Pretty JSON export of the loaded prune status dict."""
    if not isinstance(status, Mapping):
        return "{}"
    return json.dumps(dict(status), indent=2, ensure_ascii=False)


def prune_status_summary_rows_csv(rows: Sequence[Mapping[str, str]]) -> str:
    """Serialize summary field/value rows to CSV (UTF-8 text)."""
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_PRUNE_STATUS_SUMMARY_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow(
                {k: r.get(k, "") for k in _PRUNE_STATUS_SUMMARY_CSV_COLUMNS},
            )
    return buf.getvalue()


def _parse_wrote_at(raw: Any) -> datetime | None:
    if not isinstance(raw, str) or not raw:
        return None
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def prune_status_age_since_wrote_at_caption(
    status: Mapping[str, Any] | None,
    *,
    now: datetime | None = None,
) -> str | None:
    """Hours/minutes since ``wrote_at`` (complements freshness caption)."""
    if not status:
        return None
    wrote_at = _parse_wrote_at(status.get("wrote_at"))
    if wrote_at is None:
        return None
    if wrote_at.tzinfo is None:
        wrote_at = wrote_at.replace(tzinfo=timezone.utc)
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    delta = current - wrote_at
    total_seconds = max(int(delta.total_seconds()), 0)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    if hours > 0:
        age = f"{hours}h {minutes}m"
    else:
        age = f"{minutes}m"
    return f"Age since wrote_at: {age} ({total_seconds}s)."


def prune_status_pattern_filter_caption(
    status: Mapping[str, Any] | None,
) -> str | None:
    """Compact rollup of include/exclude pattern counts from prune status JSON."""
    if not status:
        return None
    inc = status.get("include_pattern_count")
    exc = status.get("exclude_pattern_count")
    inc_n: int | None = None
    exc_n: int | None = None
    if isinstance(inc, int) and not isinstance(inc, bool):
        inc_n = inc
    if isinstance(exc, int) and not isinstance(exc, bool):
        exc_n = exc
    if inc_n is None and exc_n is None:
        inc_list = status.get("include_patterns")
        exc_list = status.get("exclude_patterns")
        if isinstance(inc_list, list):
            inc_n = len(inc_list)
        if isinstance(exc_list, list):
            exc_n = len(exc_list)
    if inc_n is None and exc_n is None:
        return None
    parts: list[str] = []
    if inc_n is not None:
        parts.append(f"{inc_n} include pattern(s)")
    if exc_n is not None:
        parts.append(f"{exc_n} exclude pattern(s)")
    if not parts:
        return None
    return "Prune pattern filters: " + ", ".join(parts) + "."


def prune_status_max_age_days_caption(
    status: Mapping[str, Any] | None,
) -> str | None:
    """Surface ``max_age_days`` from the prune JSON summary."""
    if not isinstance(status, Mapping):
        return None
    raw = status.get("max_age_days")
    if not isinstance(raw, int) or isinstance(raw, bool) or raw < 1:
        return None
    suffix = "day" if raw == 1 else "days"
    return f"Prune max age cutoff: **{raw}** {suffix}."


def prune_status_retention_policy_caption(
    status: Mapping[str, Any] | None,
) -> str | None:
    """Compact retention-policy caption derived from ``max_age_days``."""
    if not isinstance(status, Mapping):
        return None
    raw = status.get("max_age_days")
    if not isinstance(raw, int) or isinstance(raw, bool) or raw < 1:
        return None
    suffix = "day" if raw == 1 else "days"
    return f"Retention policy: remove artifacts older than **{raw}** {suffix}."


def prune_status_retention_execution_caption(
    status: Mapping[str, Any] | None,
) -> str | None:
    """Retention execution mode from prune JSON summary."""
    if not isinstance(status, Mapping):
        return None
    mode = status.get("retention_execution_mode")
    if not isinstance(mode, str) or not mode.strip():
        return None
    return f"Retention execution: {mode.strip()}."


def prune_status_object_store_prune_caption(
    status: Mapping[str, Any] | None,
) -> str | None:
    """Object-store mirror delete counts from prune JSON summary."""
    if not isinstance(status, Mapping):
        return None
    attempted = status.get("object_store_attempted")
    removed = status.get("object_store_removed")
    failed = status.get("object_store_failed")
    last_error = status.get("object_store_last_error")
    lifecycle_state = status.get("retention_lifecycle_state")
    if not isinstance(attempted, int) or isinstance(attempted, bool):
        return None
    if not isinstance(removed, int) or isinstance(removed, bool):
        return None
    if failed is not None and (not isinstance(failed, int) or isinstance(failed, bool)):
        return None
    failed_n = failed if isinstance(failed, int) else 0
    parts = [
        f"Object-store prune mirror: attempted={attempted}, removed={removed}, failed={failed_n}",
    ]
    if isinstance(last_error, str) and last_error.strip():
        parts.append(f"last_error={last_error.strip()}")
    if isinstance(lifecycle_state, str) and lifecycle_state.strip():
        parts.append(f"lifecycle_state={lifecycle_state.strip()}")
    return ", ".join(parts) + "."


def prune_status_retention_alert_caption(
    status: Mapping[str, Any] | None,
) -> str | None:
    """Retention alert and stale-volume rollup from prune JSON summary."""
    if not isinstance(status, Mapping):
        return None
    level = status.get("retention_alert_level")
    if not isinstance(level, str) or not level.strip() or level.strip() == "none":
        return None
    stale_n = status.get("retention_stale_file_count")
    stale_b = status.get("retention_stale_bytes")
    exec_mode = status.get("retention_execution_mode")
    lifecycle = status.get("retention_lifecycle_state")
    parts = [f"level={level.strip()}"]
    if isinstance(stale_n, int) and not isinstance(stale_n, bool):
        parts.append(f"stale_files={stale_n}")
    if isinstance(stale_b, int) and not isinstance(stale_b, bool):
        parts.append(f"stale_bytes={stale_b}")
    if isinstance(exec_mode, str) and exec_mode.strip():
        parts.append(f"execution_mode={exec_mode.strip()}")
    if isinstance(lifecycle, str) and lifecycle.strip():
        parts.append(f"lifecycle={lifecycle.strip()}")
    return "Prune retention alert: " + ", ".join(parts) + "."


def scraper_artifact_inventory_retention_execution_caption(
    inventory: Mapping[str, Any] | None,
) -> str | None:
    """Retention execution mode from scraper artifact inventory API."""
    if not isinstance(inventory, Mapping):
        return None
    mode = inventory.get("retention_execution_mode")
    if not isinstance(mode, str) or not mode.strip():
        return None
    return f"Scraper retention execution: {mode.strip()}."


def scraper_artifact_inventory_retention_alert_caption(
    inventory: Mapping[str, Any] | None,
) -> str | None:
    """Retention alert level from scraper artifact inventory API."""
    if not isinstance(inventory, Mapping):
        return None
    level = inventory.get("retention_alert_level")
    if not isinstance(level, str) or not level.strip() or level.strip() == "none":
        return None
    stale_n = inventory.get("retention_stale_file_count")
    stale_b = inventory.get("retention_stale_bytes")
    exec_mode = inventory.get("retention_execution_mode")
    parts = [f"level={level.strip()}"]
    if isinstance(stale_n, int) and not isinstance(stale_n, bool):
        parts.append(f"stale_files={stale_n}")
    if isinstance(stale_b, int) and not isinstance(stale_b, bool):
        parts.append(f"stale_bytes={stale_b}")
    if isinstance(exec_mode, str) and exec_mode.strip():
        parts.append(f"execution_mode={exec_mode.strip()}")
    return "Scraper retention alert: " + ", ".join(parts) + "."


def scraper_artifact_inventory_storage_caption(
    inventory: Mapping[str, Any] | None,
) -> str | None:
    """One-line storage backend readiness from scraper artifact inventory."""
    if not isinstance(inventory, Mapping):
        return None
    backend = inventory.get("storage_backend")
    if not isinstance(backend, str) or not backend.strip():
        return None
    configured = inventory.get("object_store_configured")
    ready = inventory.get("object_store_ready")
    prune_requested = inventory.get("object_store_prune_requested")
    prune_effective = inventory.get("object_store_prune_effective")
    timeout_seconds = inventory.get("object_store_timeout_seconds")
    delete_attempts = inventory.get("object_store_delete_max_attempts")
    parts = [f"backend={backend.strip()}"]
    if isinstance(configured, bool):
        parts.append(f"configured={configured}")
    if isinstance(ready, bool):
        parts.append(f"ready={ready}")
    if isinstance(prune_requested, bool):
        parts.append(f"prune_requested={prune_requested}")
    if isinstance(prune_effective, bool):
        parts.append(f"prune_effective={prune_effective}")
    if isinstance(timeout_seconds, int) and not isinstance(timeout_seconds, bool):
        parts.append(f"timeout_s={timeout_seconds}")
    if isinstance(delete_attempts, int) and not isinstance(delete_attempts, bool):
        parts.append(f"delete_attempts={delete_attempts}")
    return "Scraper artifact storage: " + ", ".join(parts) + "."


def prune_status_wrote_at_caption(
    status: Mapping[str, Any] | None,
) -> str | None:
    """UTC ``wrote_at`` timestamp from the prune JSON summary."""
    if not isinstance(status, Mapping):
        return None
    raw = status.get("wrote_at")
    if not isinstance(raw, str):
        return None
    text = raw.strip()
    if not text:
        return None
    return f"Prune status wrote_at: `{text}`."


def prune_status_dry_run_caption(
    status: Mapping[str, Any] | None,
) -> str | None:
    """Dedicated ``dry_run`` flag from the prune JSON summary (no ``pruned`` count required)."""
    if not isinstance(status, Mapping):
        return None
    dry = status.get("dry_run")
    if dry is True:
        return "Prune dry_run: **yes** (no paths removed on disk)."
    if dry is False:
        return "Prune dry_run: **no** (paths may have been removed)."
    return None


def prune_status_pruned_outcome_caption(
    status: Mapping[str, Any] | None,
) -> str | None:
    """Last prune outcome: path count removed and whether the run was a dry run."""
    if not isinstance(status, Mapping):
        return None
    pruned = status.get("pruned")
    if not isinstance(pruned, int) or isinstance(pruned, bool) or pruned < 0:
        return None
    dry = status.get("dry_run")
    if dry is True:
        dry_label = "yes"
    elif dry is False:
        dry_label = "no"
    else:
        dry_label = "unknown"
    suffix = "path" if pruned == 1 else "paths"
    return (
        f"Last prune: **{pruned}** {suffix} removed, dry_run=**{dry_label}**."
    )


def prune_status_base_dir_caption(
    status: Mapping[str, Any] | None,
) -> str | None:
    """Prune target base directory from the JSON summary."""
    if not isinstance(status, Mapping):
        return None
    raw = status.get("base")
    if not isinstance(raw, str):
        return None
    text = raw.strip()
    if not text:
        return None
    return f"Prune base directory: `{text}`."


def prune_status_freshness_caption(
    status: Mapping[str, Any] | None,
    *,
    now: datetime | None = None,
    stale_after_hours: int = 24,
) -> str:
    """Operator-readable freshness blurb derived from ``wrote_at`` + injected ``now``.

    Three branches:

    * ``status`` is falsy ⇒ "No prune status file yet (run scripts/prune_scraper_artifacts.py
      with --summary-path or HERMES_PRUNE_STATUS_PATH set)."
    * ``wrote_at`` missing / unparseable ⇒ "Status file present but missing wrote_at timestamp."
    * Otherwise ⇒ "Last updated N minute(s)/hour(s) ago." with a "Stale (>24h)." suffix when
      the delta exceeds ``stale_after_hours``.

    ``now`` is injected so the caption is deterministic in tests; falls back to
    ``datetime.now(timezone.utc)`` for live rendering. Timezone-naive ``wrote_at``
    strings are treated as UTC (matches what the script writes via
    ``datetime.now(timezone.utc).isoformat()``).
    """
    if not status:
        return (
            "No prune status file yet (run scripts/prune_scraper_artifacts.py "
            "with --summary-path or HERMES_PRUNE_STATUS_PATH set)."
        )
    wrote_at = _parse_wrote_at(status.get("wrote_at"))
    if wrote_at is None:
        return "Status file present but missing wrote_at timestamp."
    if wrote_at.tzinfo is None:
        wrote_at = wrote_at.replace(tzinfo=timezone.utc)
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    delta = current - wrote_at
    total_seconds = max(int(delta.total_seconds()), 0)
    if total_seconds < 60:
        age = f"{total_seconds} second{'s' if total_seconds != 1 else ''}"
    elif total_seconds < 3600:
        minutes = total_seconds // 60
        age = f"{minutes} minute{'s' if minutes != 1 else ''}"
    else:
        hours = total_seconds // 3600
        age = f"{hours} hour{'s' if hours != 1 else ''}"
    stale_suffix = (
        f" Stale (>{stale_after_hours}h)."
        if total_seconds > stale_after_hours * 3600
        else ""
    )
    return f"Last updated {age} ago.{stale_suffix}"


def _prune_status_is_stale(
    status: Mapping[str, Any] | None,
    *,
    now: datetime | None = None,
    stale_after_hours: int = 24,
) -> bool:
    """True when ``wrote_at`` is older than ``stale_after_hours`` (matches freshness caption)."""
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
    if isinstance(raw, int) and not isinstance(raw, bool):
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
    """Rollup counts for operator summary from prune JSON status file."""
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
    if isinstance(pruned, int) and not isinstance(pruned, bool) and pruned >= 0:
        metrics["pruned"] = pruned
    dry = status.get("dry_run")
    if isinstance(dry, bool):
        metrics["dry_run"] = dry
    max_age = status.get("max_age_days")
    if isinstance(max_age, int) and not isinstance(max_age, bool) and max_age >= 1:
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
    if isinstance(schema, int) and not isinstance(schema, bool) and schema > 0:
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
    if isinstance(stale_n, int) and not isinstance(stale_n, bool) and stale_n >= 0:
        metrics["retention_stale_file_count"] = stale_n
    stale_b = status.get("retention_stale_bytes")
    if isinstance(stale_b, int) and not isinstance(stale_b, bool) and stale_b >= 0:
        metrics["retention_stale_bytes"] = stale_b
    lifecycle = status.get("retention_lifecycle_state")
    if isinstance(lifecycle, str) and lifecycle.strip():
        metrics["retention_lifecycle_state"] = lifecycle.strip()
    return metrics


def prune_status_operator_metrics_table_rows(
    metrics: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    """Two-column rows for ``st.dataframe`` (field / value)."""
    if not isinstance(metrics, Mapping):
        return []
    rows: list[dict[str, str]] = []
    pruned = metrics.get("pruned")
    if isinstance(pruned, int) and not isinstance(pruned, bool):
        rows.append({"field": "Pruned paths", "value": str(pruned)})
    dry = metrics.get("dry_run")
    if isinstance(dry, bool):
        rows.append({"field": "Dry run", "value": str(dry).lower()})
    max_age = metrics.get("max_age_days")
    if isinstance(max_age, int) and not isinstance(max_age, bool):
        rows.append({"field": "Max age (days)", "value": str(max_age)})
    inc = metrics.get("include_pattern_count", 0)
    if isinstance(inc, int) and not isinstance(inc, bool) and inc > 0:
        rows.append({"field": "Include patterns", "value": str(inc)})
    exc = metrics.get("exclude_pattern_count", 0)
    if isinstance(exc, int) and not isinstance(exc, bool) and exc > 0:
        rows.append({"field": "Exclude patterns", "value": str(exc)})
    schema = metrics.get("schema_version")
    if isinstance(schema, int) and not isinstance(schema, bool):
        rows.append({"field": "Schema version", "value": str(schema)})
    if metrics.get("is_stale") is True:
        rows.append({"field": "Stale (>24h)", "value": "yes"})
    alert_level = metrics.get("retention_alert_level")
    if isinstance(alert_level, str) and alert_level.strip() and alert_level.strip() != "none":
        rows.append({"field": "Retention alert level", "value": alert_level.strip()})
    stale_n = metrics.get("retention_stale_file_count")
    if isinstance(stale_n, int) and not isinstance(stale_n, bool):
        rows.append({"field": "Retention stale files", "value": str(stale_n)})
    stale_b = metrics.get("retention_stale_bytes")
    if isinstance(stale_b, int) and not isinstance(stale_b, bool):
        rows.append({"field": "Retention stale bytes", "value": str(stale_b)})
    lifecycle = metrics.get("retention_lifecycle_state")
    if isinstance(lifecycle, str) and lifecycle.strip():
        rows.append({"field": "Retention lifecycle", "value": lifecycle.strip()})
    return rows


def prune_status_operator_metrics_caption(
    metrics: Mapping[str, Any] | None,
) -> str | None:
    """One-line operator caption from prune rollup metrics."""
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


_PRUNE_STATUS_OPERATOR_METRICS_CSV_COLUMNS: tuple[str, ...] = ("field", "value")


def prune_status_operator_metrics_export_json(
    metrics: Mapping[str, Any] | None,
) -> str:
    """Pretty JSON for prune status operator metrics."""
    if not isinstance(metrics, Mapping):
        return "{}"
    return json.dumps(dict(metrics), indent=2, ensure_ascii=False)


def prune_status_operator_metrics_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    """Serialize prune status operator metrics rows to CSV."""
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_PRUNE_STATUS_OPERATOR_METRICS_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow(
                {
                    k: r.get(k, "")
                    for k in _PRUNE_STATUS_OPERATOR_METRICS_CSV_COLUMNS
                },
            )
    return buf.getvalue()


def prune_status_operator_metrics_export_filename_slug() -> str:
    """Stable slug for prune status operator metrics download filenames."""
    return "prune_status_operator_metrics"

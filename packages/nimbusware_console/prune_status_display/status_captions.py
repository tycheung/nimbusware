from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agent_core.coercion import is_strict_int
from nimbusware_console.components.operator_metrics import mapping_export_json
from nimbusware_console.explainer_core.display_common import stringify_display_value as _stringify
from nimbusware_console.explainer_core.table_rows_csv import field_value_table_rows_csv

SCRAPER_ARTIFACT_PRUNE_WORKFLOW_RELPATH = ".github/workflows/scraper_artifact_prune.yml"


def prune_scraper_artifact_prune_workflow_caption() -> str:
    return (
        f"Scheduled prune workflow: ``{SCRAPER_ARTIFACT_PRUNE_WORKFLOW_RELPATH}`` "
        "(cron / workflow_dispatch; not default CI)."
    )


def prune_status_schema_version_caption(
    status: Mapping[str, Any] | None,
) -> str | None:
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


def load_prune_status(path: Path | None) -> dict[str, Any] | None:
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
    if not status:
        return []
    rows: list[dict[str, str]] = []
    for key, label in _PRUNE_STATUS_FIELDS:
        if key not in status:
            continue
        rows.append({"field": label, "value": _stringify(status.get(key))})
    return rows


def prune_status_export_json(status: Mapping[str, Any] | None) -> str:
    return mapping_export_json(status)


prune_status_summary_rows_csv = field_value_table_rows_csv


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
    if not status:
        return None
    inc = status.get("include_pattern_count")
    exc = status.get("exclude_pattern_count")
    inc_n: int | None = None
    exc_n: int | None = None
    if is_strict_int(inc):
        inc_n = inc
    if is_strict_int(exc):
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
    if not isinstance(status, Mapping):
        return None
    mode = status.get("retention_execution_mode")
    if not isinstance(mode, str) or not mode.strip():
        return None
    return f"Retention execution: {mode.strip()}."


def prune_status_object_store_prune_caption(
    status: Mapping[str, Any] | None,
) -> str | None:
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
    if is_strict_int(stale_n):
        parts.append(f"stale_files={stale_n}")
    if is_strict_int(stale_b):
        parts.append(f"stale_bytes={stale_b}")
    if isinstance(exec_mode, str) and exec_mode.strip():
        parts.append(f"execution_mode={exec_mode.strip()}")
    if isinstance(lifecycle, str) and lifecycle.strip():
        parts.append(f"lifecycle={lifecycle.strip()}")
    return "Prune retention alert: " + ", ".join(parts) + "."


def scraper_artifact_inventory_retention_execution_caption(
    inventory: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(inventory, Mapping):
        return None
    mode = inventory.get("retention_execution_mode")
    if not isinstance(mode, str) or not mode.strip():
        return None
    return f"Scraper retention execution: {mode.strip()}."


def scraper_artifact_inventory_retention_alert_caption(
    inventory: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(inventory, Mapping):
        return None
    level = inventory.get("retention_alert_level")
    if not isinstance(level, str) or not level.strip() or level.strip() == "none":
        return None
    stale_n = inventory.get("retention_stale_file_count")
    stale_b = inventory.get("retention_stale_bytes")
    exec_mode = inventory.get("retention_execution_mode")
    parts = [f"level={level.strip()}"]
    if is_strict_int(stale_n):
        parts.append(f"stale_files={stale_n}")
    if is_strict_int(stale_b):
        parts.append(f"stale_bytes={stale_b}")
    if isinstance(exec_mode, str) and exec_mode.strip():
        parts.append(f"execution_mode={exec_mode.strip()}")
    return "Scraper retention alert: " + ", ".join(parts) + "."

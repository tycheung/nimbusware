from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from agent_core.coercion import is_strict_int
from nimbusware_console.explainer_core.metrics_scaffold import metrics_caption, metrics_table_rows
from nimbusware_console.explainer_core.operator_metrics_exports import bind_operator_metrics_exports
from nimbusware_console.explainer_core.schema_metrics import build_operator_metrics
from nimbusware_console.run_escalated.rows import (
    run_escalated_delta_export_filename_slug,
    run_escalated_export_filename_slug,
    run_escalated_history_export_filename_slug,
)

_RUN_ESCALATED_DEFAULTS: dict[str, Any] = {
    "notes_present": False,
    "actor_id_present": False,
    "reason_code_present": False,
    "policy_snapshot_id_present": False,
    "event_id_present": False,
    "severity": None,
}

_RUN_ESCALATED_STR_PRESENT: tuple[tuple[str, str], ...] = (
    ("notes", "notes_present"),
    ("actor_id", "actor_id_present"),
)

_RUN_ESCALATED_BOOL_ROWS: tuple[tuple[str, str], ...] = (
    ("Reason code present", "reason_code_present"),
    ("Actor id present", "actor_id_present"),
    ("Policy snapshot id present", "policy_snapshot_id_present"),
    ("Event id present", "event_id_present"),
    ("Notes present", "notes_present"),
)

_HISTORY_DEFAULTS: dict[str, Any] = {
    "entry_count": 0,
    "distinct_reason_codes": 0,
    "distinct_actor_ids": 0,
    "notes_present_count": 0,
}

_HISTORY_TABLE_ROWS: tuple[tuple[str, str], ...] = (
    ("Entry count", "entry_count"),
    ("Distinct reason codes", "distinct_reason_codes"),
    ("Distinct actor ids", "distinct_actor_ids"),
    ("Notes present", "notes_present_count"),
)

_DELTA_BOOL_ROWS: tuple[tuple[str, str], ...] = (
    ("Has previous event", "has_previous"),
    ("Has current event", "has_current"),
)

_DELTA_CHANGED_ROWS: tuple[tuple[str, str], ...] = (
    ("Reason code changed", "reason_code_changed"),
    ("Actor id changed", "actor_id_changed"),
    ("Policy snapshot id changed", "policy_snapshot_id_changed"),
)


def run_escalated_operator_metrics(
    summary: Mapping[str, Any] | None,
) -> dict[str, Any]:
    metrics = build_operator_metrics(
        summary,
        _RUN_ESCALATED_DEFAULTS,
        str_present=_RUN_ESCALATED_STR_PRESENT,
    )
    if isinstance(summary, Mapping):
        for payload_key, metric_key in (
            ("reason_code", "reason_code_present"),
            ("policy_snapshot_id", "policy_snapshot_id_present"),
            ("event_id", "event_id_present"),
        ):
            raw = summary.get(payload_key)
            metrics[metric_key] = raw is not None and str(raw).strip() != ""
        sev = summary.get("severity")
        if isinstance(sev, str) and sev.strip():
            metrics["severity"] = sev.strip()
    return metrics


def run_escalated_operator_metrics_table_rows(
    metrics: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    if not isinstance(metrics, Mapping):
        return []
    rows: list[dict[str, str]] = []
    sev = metrics.get("severity")
    if isinstance(sev, str) and sev.strip():
        rows.append({"field": "Severity", "value": sev.strip()})
    rows.extend(
        metrics_table_rows(
            metrics,
            _RUN_ESCALATED_BOOL_ROWS,
            include_when=lambda m, k: m.get(k) is True,
        ),
    )
    return rows


def run_escalated_operator_metrics_caption(
    metrics: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(metrics, Mapping):
        return None
    sev = metrics.get("severity")
    if isinstance(sev, str) and sev.strip():
        return f"Run escalated: severity **{sev.strip()}**."
    present: list[str] = []
    if metrics.get("reason_code_present") is True:
        present.append("reason code")
    if metrics.get("actor_id_present") is True:
        present.append("actor")
    if metrics.get("policy_snapshot_id_present") is True:
        present.append("policy snapshot")
    if metrics.get("event_id_present") is True:
        present.append("event id")
    if metrics.get("notes_present") is True:
        present.append("notes")
    if not present:
        return None
    return "Run escalated metrics: " + ", ".join(present) + " present."


def run_escalated_operator_metrics_export_filename_slug(
    run_id: str,
    *,
    max_len: int = 36,
) -> str:
    return run_escalated_export_filename_slug(run_id, max_len=max_len)


def run_escalated_history_operator_metrics(
    history: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    metrics = build_operator_metrics(None, _HISTORY_DEFAULTS)
    if not history:
        return metrics
    reasons: set[str] = set()
    actors: set[str] = set()
    for entry in history:
        if not isinstance(entry, dict):
            continue
        metrics["entry_count"] = int(metrics["entry_count"]) + 1
        rc = entry.get("reason_code")
        if rc is not None and str(rc).strip():
            reasons.add(str(rc).strip())
        actor = entry.get("actor_id")
        if isinstance(actor, str) and actor.strip():
            actors.add(actor.strip())
        notes = entry.get("notes")
        if isinstance(notes, str) and notes.strip():
            metrics["notes_present_count"] = int(metrics["notes_present_count"]) + 1
    metrics["distinct_reason_codes"] = len(reasons)
    metrics["distinct_actor_ids"] = len(actors)
    return metrics


def run_escalated_history_operator_metrics_table_rows(
    metrics: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    return metrics_table_rows(metrics, _HISTORY_TABLE_ROWS, bool_lower=False)


def run_escalated_history_operator_metrics_caption(
    metrics: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(metrics, Mapping):
        return None
    ec = metrics.get("entry_count")
    if isinstance(ec, bool) or not isinstance(ec, int) or ec < 1:
        return None
    parts = [f"**{ec}** escalation(s)"]
    drc = metrics.get("distinct_reason_codes", 0)
    if is_strict_int(drc) and drc > 0:
        parts.append(f"**{drc}** distinct reason code(s)")
    npc = metrics.get("notes_present_count", 0)
    if is_strict_int(npc) and npc > 0:
        parts.append(f"**{npc}** with notes")
    dac = metrics.get("distinct_actor_ids", 0)
    if is_strict_int(dac) and dac > 0:
        word = "actor" if dac == 1 else "actors"
        parts.append(f"**{dac}** distinct {word}")
    return metrics_caption("Run escalated history metrics: ", parts)


def run_escalated_history_operator_metrics_export_filename_slug(
    run_id: str,
    *,
    max_len: int = 36,
) -> str:
    return run_escalated_history_export_filename_slug(run_id, max_len=max_len)


def run_escalated_delta_operator_metrics(
    delta: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if not isinstance(delta, Mapping):
        return {"present": False}
    prev_id = delta.get("previous_event_id")
    cur_id = delta.get("current_event_id")
    return {
        "present": True,
        "has_previous": bool(prev_id is not None and str(prev_id).strip()),
        "has_current": bool(cur_id is not None and str(cur_id).strip()),
        "reason_code_changed": bool(delta.get("reason_code_changed"))
        if "reason_code_changed" in delta
        else None,
        "actor_id_changed": bool(delta.get("actor_id_changed"))
        if "actor_id_changed" in delta
        else None,
        "policy_snapshot_id_changed": bool(delta.get("policy_snapshot_id_changed"))
        if "policy_snapshot_id_changed" in delta
        else None,
    }


def run_escalated_delta_operator_metrics_table_rows(
    metrics: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    if not isinstance(metrics, Mapping) or not metrics.get("present"):
        return []
    rows = metrics_table_rows(
        metrics,
        _DELTA_BOOL_ROWS,
        include_when=lambda m, k: m.get(k) is True,
    )
    rows.extend(
        metrics_table_rows(
            metrics,
            _DELTA_CHANGED_ROWS,
            include_when=lambda _m, k: isinstance(metrics.get(k), bool),
        ),
    )
    return rows


def run_escalated_delta_operator_metrics_caption(
    metrics: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(metrics, Mapping) or not metrics.get("present"):
        return None
    changed: list[str] = []
    for key, label in (
        ("reason_code_changed", "reason code"),
        ("actor_id_changed", "actor id"),
        ("policy_snapshot_id_changed", "policy snapshot id"),
    ):
        if metrics.get(key) is True:
            changed.append(label)
    if not changed:
        stable: list[str] = []
        if metrics.get("has_previous") is True and metrics.get("has_current") is True:
            stable.append("previous and current events present")
        elif metrics.get("has_current") is True:
            stable.append("current event only")
        if not stable:
            return None
        return "Run escalated delta metrics: no field changes (" + ", ".join(stable) + ")."
    return metrics_caption("Run escalated delta metrics: changed ", changed)


def run_escalated_delta_operator_metrics_export_filename_slug(
    run_id: str,
    *,
    max_len: int = 36,
) -> str:
    return run_escalated_delta_export_filename_slug(run_id, max_len=max_len)


(
    run_escalated_operator_metrics_export_json,
    run_escalated_operator_metrics_table_rows_csv,
    _run_escalated_operator_metrics_exports_slug,
) = bind_operator_metrics_exports(export_slug="run_escalated_operator_metrics")

(
    run_escalated_history_operator_metrics_export_json,
    run_escalated_history_operator_metrics_table_rows_csv,
    _run_escalated_history_operator_metrics_exports_slug,
) = bind_operator_metrics_exports(export_slug="run_escalated_history_operator_metrics")

(
    run_escalated_delta_operator_metrics_export_json,
    run_escalated_delta_operator_metrics_table_rows_csv,
    _run_escalated_delta_operator_metrics_exports_slug,
) = bind_operator_metrics_exports(export_slug="run_escalated_delta_operator_metrics")

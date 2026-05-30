from __future__ import annotations

import csv
import json
import re
from collections.abc import Mapping, Sequence
from io import StringIO
from pathlib import Path
from typing import Any

from nimbusware_console.run_escalated.rows import (
    run_escalated_delta_export_filename_slug,
    run_escalated_export_filename_slug,
    run_escalated_history_export_filename_slug,
)

def run_escalated_operator_metrics(
    summary: Mapping[str, Any] | None,
) -> dict[str, Any]:
    metrics: dict[str, Any] = {
        "notes_present": False,
        "actor_id_present": False,
        "reason_code_present": False,
        "policy_snapshot_id_present": False,
        "event_id_present": False,
        "severity": None,
    }
    if not isinstance(summary, Mapping):
        return metrics
    notes = summary.get("notes")
    metrics["notes_present"] = isinstance(notes, str) and bool(notes.strip())
    actor = summary.get("actor_id")
    metrics["actor_id_present"] = isinstance(actor, str) and bool(actor.strip())
    rc = summary.get("reason_code")
    metrics["reason_code_present"] = rc is not None and str(rc).strip() != ""
    policy = summary.get("policy_snapshot_id")
    metrics["policy_snapshot_id_present"] = (
        policy is not None and str(policy).strip() != ""
    )
    eid = summary.get("event_id")
    metrics["event_id_present"] = eid is not None and str(eid).strip() != ""
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
    for key, label in (
        ("reason_code_present", "Reason code present"),
        ("actor_id_present", "Actor id present"),
        ("policy_snapshot_id_present", "Policy snapshot id present"),
        ("event_id_present", "Event id present"),
        ("notes_present", "Notes present"),
    ):
        if metrics.get(key) is True:
            rows.append({"field": label, "value": "yes"})
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


_RUN_ESCALATED_OPERATOR_METRICS_CSV_COLUMNS: tuple[str, ...] = ("field", "value")




def run_escalated_operator_metrics_export_json(
    metrics: Mapping[str, Any] | None,
) -> str:
    if not isinstance(metrics, Mapping):
        return "{}"
    return json.dumps(dict(metrics), indent=2, ensure_ascii=False)




def run_escalated_operator_metrics_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_RUN_ESCALATED_OPERATOR_METRICS_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow(
                {
                    k: r.get(k, "")
                    for k in _RUN_ESCALATED_OPERATOR_METRICS_CSV_COLUMNS
                },
            )
    return buf.getvalue()




def run_escalated_operator_metrics_export_filename_slug(
    run_id: str,
    *,
    max_len: int = 36,
) -> str:
    return run_escalated_export_filename_slug(run_id, max_len=max_len)




def run_escalated_history_operator_metrics(
    history: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    metrics: dict[str, Any] = {
        "entry_count": 0,
        "distinct_reason_codes": 0,
        "distinct_actor_ids": 0,
        "notes_present_count": 0,
    }
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
    if not isinstance(metrics, Mapping):
        return []
    rows: list[dict[str, str]] = [
        {"field": "Entry count", "value": str(metrics.get("entry_count", 0))},
        {
            "field": "Distinct reason codes",
            "value": str(metrics.get("distinct_reason_codes", 0)),
        },
        {
            "field": "Distinct actor ids",
            "value": str(metrics.get("distinct_actor_ids", 0)),
        },
        {
            "field": "Notes present",
            "value": str(metrics.get("notes_present_count", 0)),
        },
    ]
    return rows




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
    if isinstance(drc, int) and not isinstance(drc, bool) and drc > 0:
        parts.append(f"**{drc}** distinct reason code(s)")
    npc = metrics.get("notes_present_count", 0)
    if isinstance(npc, int) and not isinstance(npc, bool) and npc > 0:
        parts.append(f"**{npc}** with notes")
    dac = metrics.get("distinct_actor_ids", 0)
    if isinstance(dac, int) and not isinstance(dac, bool) and dac > 0:
        word = "actor" if dac == 1 else "actors"
        parts.append(f"**{dac}** distinct {word}")
    return "Run escalated history metrics: " + ", ".join(parts) + "."


_RUN_ESCALATED_HISTORY_OPERATOR_METRICS_CSV_COLUMNS: tuple[str, ...] = (
    "field",
    "value",
)




def run_escalated_history_operator_metrics_export_json(
    metrics: Mapping[str, Any] | None,
) -> str:
    if not isinstance(metrics, Mapping):
        return "{}"
    return json.dumps(dict(metrics), indent=2, ensure_ascii=False)




def run_escalated_history_operator_metrics_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_RUN_ESCALATED_HISTORY_OPERATOR_METRICS_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow(
                {
                    k: r.get(k, "")
                    for k in _RUN_ESCALATED_HISTORY_OPERATOR_METRICS_CSV_COLUMNS
                },
            )
    return buf.getvalue()




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
    rows: list[dict[str, str]] = []
    if metrics.get("has_previous") is True:
        rows.append({"field": "Has previous event", "value": "yes"})
    if metrics.get("has_current") is True:
        rows.append({"field": "Has current event", "value": "yes"})
    for key, label in (
        ("reason_code_changed", "Reason code changed"),
        ("actor_id_changed", "Actor id changed"),
        ("policy_snapshot_id_changed", "Policy snapshot id changed"),
    ):
        val = metrics.get(key)
        if isinstance(val, bool):
            rows.append({"field": label, "value": str(val).lower()})
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
    return "Run escalated delta metrics: changed " + ", ".join(changed) + "."


_RUN_ESCALATED_DELTA_OPERATOR_METRICS_CSV_COLUMNS: tuple[str, ...] = (
    "field",
    "value",
)




def run_escalated_delta_operator_metrics_export_json(
    metrics: Mapping[str, Any] | None,
) -> str:
    if not isinstance(metrics, Mapping):
        return "{}"
    return json.dumps(dict(metrics), indent=2, ensure_ascii=False)




def run_escalated_delta_operator_metrics_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_RUN_ESCALATED_DELTA_OPERATOR_METRICS_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow(
                {
                    k: r.get(k, "")
                    for k in _RUN_ESCALATED_DELTA_OPERATOR_METRICS_CSV_COLUMNS
                },
            )
    return buf.getvalue()




def run_escalated_delta_operator_metrics_export_filename_slug(
    run_id: str,
    *,
    max_len: int = 36,
) -> str:
    return run_escalated_delta_export_filename_slug(run_id, max_len=max_len)

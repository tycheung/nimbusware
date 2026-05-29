"""Run escalated summary for Streamlit (plan §14 #19).

Parity with timeline top-level ``run_escalated`` from the HTTP API.
"""

from __future__ import annotations

import csv
import json
import re
from collections.abc import Mapping, Sequence
from io import StringIO
from pathlib import Path
from typing import Any

# Order matches ``run_escalated_timeline_summary`` in runs (human-facing first).
_RUN_ESCALATED_FIELDS: tuple[tuple[str, str], ...] = (
    ("actor_id", "Actor id"),
    ("reason_code", "Reason code"),
    ("policy_snapshot_id", "Policy snapshot id"),
    ("notes", "Notes"),
    ("event_id", "Event id"),
    ("occurred_at", "Occurred at"),
)


def _stringify(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def run_escalated_from_timeline(
    timeline_body: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    """Return top-level ``run_escalated`` dict from a ``GET /v1/runs/…/timeline`` JSON body."""
    if not isinstance(timeline_body, Mapping):
        return None
    raw = timeline_body.get("run_escalated")
    return raw if isinstance(raw, dict) else None


def run_escalated_summary_rows(summary: Mapping[str, Any] | None) -> list[dict[str, str]]:
    """Rows suitable for ``st.dataframe`` (field / value columns)."""
    if not summary:
        return []
    rows: list[dict[str, str]] = []
    for key, label in _RUN_ESCALATED_FIELDS:
        if key not in summary:
            continue
        rows.append({"field": label, "value": _stringify(summary.get(key))})
    return rows


_RUN_ESCALATED_SUMMARY_CSV_COLUMNS: tuple[str, ...] = ("field", "value")


def run_escalated_summary_rows_csv(rows: Sequence[Mapping[str, str]]) -> str:
    """Serialize run escalated summary field/value rows to CSV (UTF-8 text)."""
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_RUN_ESCALATED_SUMMARY_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow({k: r.get(k, "") for k in _RUN_ESCALATED_SUMMARY_CSV_COLUMNS})
    return buf.getvalue()


def run_escalated_export_json(summary: Mapping[str, Any] | None) -> str:
    """JSON export of timeline top-level ``run_escalated`` summary."""
    if not isinstance(summary, Mapping):
        return "{}"
    return json.dumps(dict(summary), ensure_ascii=False, indent=2)


def run_escalated_export_filename_slug(run_id: str, *, max_len: int = 36) -> str:
    """ASCII-ish slug for run escalated summary download filenames."""
    raw = str(run_id).strip().lower()
    slug = re.sub(r"[^a-z0-9_.-]+", "_", raw).strip("._-") or "run"
    return slug[:max_len]


def run_escalated_operator_metrics(
    summary: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Rollup presence flags for latest timeline ``run_escalated`` summary."""
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
    """Two-column rows for ``st.dataframe`` (field / value)."""
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
    """One-line operator caption from latest escalation rollup."""
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
    """Pretty JSON for run escalated operator metrics."""
    if not isinstance(metrics, Mapping):
        return "{}"
    return json.dumps(dict(metrics), indent=2, ensure_ascii=False)


def run_escalated_operator_metrics_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    """Serialize run escalated operator metrics rows to CSV."""
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
    """ASCII-ish slug for run escalated operator metrics downloads."""
    return run_escalated_export_filename_slug(run_id, max_len=max_len)


def run_escalated_occurred_at_caption(summary: Mapping[str, Any] | None) -> str | None:
    """One-line ``occurred_at`` from timeline ``run_escalated``."""
    if not isinstance(summary, Mapping):
        return None
    raw = summary.get("occurred_at")
    if not isinstance(raw, str):
        return None
    text = raw.strip()
    if not text:
        return None
    return f"Run escalated at: {text}."


def run_escalated_event_id_caption(summary: Mapping[str, Any] | None) -> str | None:
    """One-line ``event_id`` from timeline ``run_escalated``."""
    if not isinstance(summary, Mapping):
        return None
    raw = summary.get("event_id")
    if not isinstance(raw, str):
        return None
    text = raw.strip()
    if not text:
        return None
    return f"Run escalated event_id: `{text}`."


def run_escalated_reason_summary_caption(
    summary: Mapping[str, Any] | None,
) -> str | None:
    """One-line reason_code / actor_id / policy_snapshot_id from timeline ``run_escalated``."""
    if not isinstance(summary, Mapping) or not summary:
        return None
    parts: list[str] = []
    rc = summary.get("reason_code")
    if rc is not None and str(rc).strip():
        parts.append(f"reason_code={str(rc).strip()}")
    actor = summary.get("actor_id")
    if isinstance(actor, str) and actor.strip():
        parts.append(f"actor_id={actor.strip()}")
    pol = summary.get("policy_snapshot_id")
    if pol is not None and str(pol).strip():
        parts.append(f"policy_snapshot_id={str(pol).strip()}")
    if not parts:
        return None
    return "Run escalated: " + ", ".join(parts) + "."


def run_escalated_notes_preview_caption(
    summary: Mapping[str, Any] | None,
    *,
    max_len: int = 120,
) -> str | None:
    """Truncated one-line preview of escalation ``notes`` when present."""
    if not isinstance(summary, Mapping):
        return None
    notes = summary.get("notes")
    if not isinstance(notes, str):
        return None
    text = notes.strip()
    if not text:
        return None
    if len(text) > max_len:
        text = text[: max_len - 1].rstrip() + "…"
    return f"Escalation notes: {text!r}."


def run_escalated_actor_without_notes_caption(summary: Mapping[str, Any] | None) -> str | None:
    """Surface timeline **run.escalated** rows that name an actor but omit free-form notes.

    Helps operators correlate **run_escalated** with ``configs/escalation/policy.yaml`` and
    Module Integrator escalation suppress explainers. Returns ``None`` when ``actor_id`` is
    missing / not a non-empty string, when ``notes`` carries non-empty text, or when
    ``notes`` is present but not a string.
    """
    if not isinstance(summary, Mapping):
        return None
    raw_actor = summary.get("actor_id")
    if not isinstance(raw_actor, str) or not raw_actor.strip():
        return None
    notes = summary.get("notes")
    if isinstance(notes, str) and notes.strip():
        return None
    if notes is not None and not isinstance(notes, str):
        return None
    return (
        "Escalation **actor_id** is set but **notes** are empty — add operator context when "
        "correlating this **run.escalated** event with ``configs/escalation/policy.yaml``."
    )


def run_escalated_policy_cross_ref_caption(
    repo_root: Path | None,
    summary: Mapping[str, Any] | None,
) -> str | None:
    """When ``policy_snapshot_id`` is set, point operators at disk policy + workflow suppress."""
    if not isinstance(summary, Mapping):
        return None
    raw = summary.get("policy_snapshot_id")
    if raw is None:
        return None
    sid = str(raw).strip()
    if not sid:
        return None
    rel = "configs/escalation/policy.yaml"
    tail = (
        f"Thresholds and counters are defined under ``{rel}`` (repo-relative). "
        "Compare **Escalation suppress (workflow + parsed)** under Module Integrator for "
        "``suppress_automatic_escalation`` vs automatic ``run.escalated`` emitters."
    )
    if repo_root is None:
        return f"**policy_snapshot_id:** ``{sid}``. {tail}"
    pol = repo_root / "configs" / "escalation" / "policy.yaml"
    if pol.is_file():
        on_disk = "policy file present on this repo root"
    else:
        on_disk = "policy file missing on this repo root"
    return f"**policy_snapshot_id:** ``{sid}`` ({on_disk}). {tail}"


def run_escalated_history_from_timeline(
    timeline_body: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    """Return ``run_escalated_history`` list from a timeline JSON body."""
    if not isinstance(timeline_body, Mapping):
        return []
    raw = timeline_body.get("run_escalated_history")
    if not isinstance(raw, list):
        return []
    return [x for x in raw if isinstance(x, dict)]


def run_escalated_history_table_rows(
    history: list[dict[str, Any]],
) -> list[dict[str, str]]:
    """Rows for ``st.dataframe`` — one row per escalation in chronological order."""
    rows: list[dict[str, str]] = []
    for i, e in enumerate(history, start=1):
        rows.append(
            {
                "#": str(i),
                "Occurred at": _stringify(e.get("occurred_at")),
                "Actor": _stringify(e.get("actor_id")),
                "Reason": _stringify(e.get("reason_code")),
                "Policy snapshot": _stringify(e.get("policy_snapshot_id")),
                "Notes": _stringify(e.get("notes")),
                "Event id": _stringify(e.get("event_id")),
            },
        )
    return rows


_RUN_ESCALATED_HISTORY_CSV_COLUMNS: tuple[str, ...] = (
    "#",
    "Occurred at",
    "Actor",
    "Reason",
    "Policy snapshot",
    "Notes",
    "Event id",
)


def run_escalated_history_table_rows_csv(rows: Sequence[Mapping[str, str]]) -> str:
    """Serialize run escalated history display rows to CSV (UTF-8 text)."""
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_RUN_ESCALATED_HISTORY_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow({k: r.get(k, "") for k in _RUN_ESCALATED_HISTORY_CSV_COLUMNS})
    return buf.getvalue()


def run_escalated_history_export_json(history: Sequence[Mapping[str, Any]]) -> str:
    """JSON export of raw ``run_escalated_history`` timeline list."""
    items = [dict(x) for x in history if isinstance(x, Mapping)]
    return json.dumps(items, ensure_ascii=False, indent=2)


def run_escalated_history_export_filename_slug(run_id: str, *, max_len: int = 36) -> str:
    """ASCII-ish slug for run escalated history download filenames."""
    raw = str(run_id).strip().lower()
    slug = re.sub(r"[^a-z0-9_.-]+", "_", raw).strip("._-") or "run"
    return slug[:max_len]


def run_escalated_history_entry_count_caption(
    history: list[dict[str, Any]] | None,
) -> str | None:
    """One-line count of escalation events in the bounded timeline history view."""
    if not history:
        return None
    n = len(history)
    word = "escalation" if n == 1 else "escalations"
    return f"Run escalated history: **{n}** {word} in this timeline view."


def run_escalated_history_operator_metrics(
    history: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    """Rollup counts for operator summary from ``run_escalated_history``."""
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
    """Two-column rows for ``st.dataframe`` (field / value)."""
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


def run_escalated_history_distinct_actors_caption(
    metrics: Mapping[str, Any] | None,
) -> str | None:
    """One-line distinct-actor count from :func:`run_escalated_history_operator_metrics`."""
    if not isinstance(metrics, Mapping):
        return None
    ec = metrics.get("entry_count")
    if isinstance(ec, bool) or not isinstance(ec, int) or ec < 1:
        return None
    dac = metrics.get("distinct_actor_ids")
    if not isinstance(dac, int) or isinstance(dac, bool) or dac < 0:
        return None
    if dac == 0:
        return "Run escalated history: no distinct actor ids in this view."
    word = "actor" if dac == 1 else "actors"
    return f"Run escalated history: **{dac}** distinct {word} across **{ec}** escalation(s)."


def run_escalated_history_operator_metrics_caption(
    metrics: Mapping[str, Any] | None,
) -> str | None:
    """One-line operator caption when history has at least one entry."""
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
    """Pretty JSON for run escalated history operator metrics."""
    if not isinstance(metrics, Mapping):
        return "{}"
    return json.dumps(dict(metrics), indent=2, ensure_ascii=False)


def run_escalated_history_operator_metrics_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    """Serialize run escalated history operator metrics rows to CSV."""
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
    """ASCII-ish slug for run escalated history operator metrics downloads."""
    return run_escalated_history_export_filename_slug(run_id, max_len=max_len)


def run_escalated_delta_from_timeline(
    timeline_body: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    """Return ``run_escalated_delta`` from a timeline JSON body."""
    if not isinstance(timeline_body, Mapping):
        return None
    raw = timeline_body.get("run_escalated_delta")
    return raw if isinstance(raw, dict) else None


# Order matches ``run_escalated_timeline_delta`` in runs (latest vs prior escalation).
_RUN_ESCALATED_DELTA_FIELDS: tuple[tuple[str, str], ...] = (
    ("previous_event_id", "Previous event id"),
    ("current_event_id", "Current event id"),
    ("reason_code_changed", "Reason code changed"),
    ("actor_id_changed", "Actor id changed"),
    ("policy_snapshot_id_changed", "Policy snapshot id changed"),
    ("previous_reason_code", "Previous reason code"),
    ("current_reason_code", "Current reason code"),
    ("previous_actor_id", "Previous actor id"),
    ("current_actor_id", "Current actor id"),
)


def run_escalated_delta_summary_rows(delta: Mapping[str, Any] | None) -> list[dict[str, str]]:
    """Rows suitable for ``st.dataframe`` / CSV — field / value from timeline delta."""
    if not isinstance(delta, Mapping):
        return []
    rows: list[dict[str, str]] = []
    for key, label in _RUN_ESCALATED_DELTA_FIELDS:
        if key not in delta:
            continue
        rows.append({"field": label, "value": _stringify(delta.get(key))})
    return rows


_RUN_ESCALATED_DELTA_SUMMARY_CSV_COLUMNS: tuple[str, ...] = ("field", "value")


def run_escalated_delta_table_rows_csv(rows: Sequence[Mapping[str, str]]) -> str:
    """Serialize run escalated delta summary rows to CSV (UTF-8 text)."""
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_RUN_ESCALATED_DELTA_SUMMARY_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow({k: r.get(k, "") for k in _RUN_ESCALATED_DELTA_SUMMARY_CSV_COLUMNS})
    return buf.getvalue()


def run_escalated_delta_export_json(delta: Mapping[str, Any] | None) -> str:
    """JSON export of timeline ``run_escalated_delta`` object."""
    if not isinstance(delta, Mapping):
        return "{}"
    return json.dumps(dict(delta), ensure_ascii=False, indent=2)


def run_escalated_delta_export_filename_slug(run_id: str, *, max_len: int = 36) -> str:
    """ASCII-ish slug for run escalated delta download filenames."""
    raw = str(run_id).strip().lower()
    slug = re.sub(r"[^a-z0-9_.-]+", "_", raw).strip("._-") or "run"
    return slug[:max_len]


def run_escalated_delta_transition_caption(
    delta: Mapping[str, Any] | None,
) -> str | None:
    """One-line summary of latest-vs-prior escalation delta."""
    if not isinstance(delta, Mapping):
        return None
    parts: list[str] = []
    if delta.get("reason_code_changed") is True:
        prev = _stringify(delta.get("previous_reason_code"))
        cur = _stringify(delta.get("current_reason_code"))
        parts.append(f"reason {prev} → {cur}")
    if delta.get("actor_id_changed") is True:
        prev_a = _stringify(delta.get("previous_actor_id"))
        cur_a = _stringify(delta.get("current_actor_id"))
        parts.append(f"actor {prev_a} → {cur_a}")
    if delta.get("policy_snapshot_id_changed") is True:
        parts.append("policy_snapshot_id changed")
    if not parts:
        return None
    return "Run escalated delta: " + "; ".join(parts) + "."


def run_escalated_delta_operator_metrics(
    delta: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Short hints on latest-vs-prior run escalation delta (read-only, JSON-serializable)."""
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
    """Two-column rows for ``st.dataframe`` (field / value)."""
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
    """One-line summary listing which escalation delta fields changed."""
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
    """Pretty JSON for run escalated delta operator metrics."""
    if not isinstance(metrics, Mapping):
        return "{}"
    return json.dumps(dict(metrics), indent=2, ensure_ascii=False)


def run_escalated_delta_operator_metrics_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    """Serialize run escalated delta operator metrics rows to CSV."""
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
    """ASCII-ish slug for run escalated delta operator metrics downloads."""
    return run_escalated_delta_export_filename_slug(run_id, max_len=max_len)

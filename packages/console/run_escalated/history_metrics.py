from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from agent_core.coercion import is_strict_int
from console.explainer_core.metrics_scaffold import metrics_caption
from console.explainer_core.schema_metrics import build_operator_metrics
from console.explainer_core.workflow_metrics_spec import (
    install_workflow_metrics_from_spec,
    repo_display_spec,
)

_HISTORY_DEFAULTS: dict[str, Any] = {
    "entry_count": 0,
    "distinct_reason_codes": 0,
    "distinct_actor_ids": 0,
    "notes_present_count": 0,
}


def _history_metrics(history: list[dict[str, Any]] | None) -> dict[str, Any]:
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


def _history_caption(metrics: Mapping[str, Any] | None) -> str | None:
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


_install_ns: dict[str, object] = {}
install_workflow_metrics_from_spec(
    _install_ns,
    repo_display_spec("run_escalated_history"),
    caption_parts_fn=lambda _m: [],
    custom_metrics_fn=_history_metrics,
    custom_caption_fn=_history_caption,
)

run_escalated_history_operator_metrics = _install_ns["run_escalated_history_operator_metrics"]
run_escalated_history_operator_metrics_table_rows = _install_ns[
    "run_escalated_history_operator_metrics_table_rows"
]
run_escalated_history_operator_metrics_caption = _install_ns[
    "run_escalated_history_operator_metrics_caption"
]
run_escalated_history_operator_metrics_export_json = _install_ns[
    "run_escalated_history_operator_metrics_export_json"
]
run_escalated_history_operator_metrics_table_rows_csv = _install_ns[
    "run_escalated_history_operator_metrics_table_rows_csv"
]

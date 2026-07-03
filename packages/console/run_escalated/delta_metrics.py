from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from console.explainer_core.metrics_scaffold import metrics_caption, metrics_table_rows
from console.explainer_core.workflow_metrics_spec import (
    install_workflow_metrics_from_spec,
    repo_display_spec,
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


def _delta_metrics(delta: Mapping[str, Any] | None) -> dict[str, Any]:
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


def _delta_table_rows(metrics: Mapping[str, Any] | None) -> list[dict[str, str]]:
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


def _delta_caption(metrics: Mapping[str, Any] | None) -> str | None:
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


_install_ns: dict[str, object] = {}
install_workflow_metrics_from_spec(
    _install_ns,
    repo_display_spec("run_escalated_delta"),
    caption_parts_fn=lambda _m: [],
    custom_metrics_fn=_delta_metrics,
    custom_table_rows_fn=_delta_table_rows,
    custom_caption_fn=_delta_caption,
)

run_escalated_delta_operator_metrics = _install_ns["run_escalated_delta_operator_metrics"]
run_escalated_delta_operator_metrics_table_rows = _install_ns[
    "run_escalated_delta_operator_metrics_table_rows"
]
run_escalated_delta_operator_metrics_caption = _install_ns[
    "run_escalated_delta_operator_metrics_caption"
]
run_escalated_delta_operator_metrics_export_json = _install_ns[
    "run_escalated_delta_operator_metrics_export_json"
]
run_escalated_delta_operator_metrics_table_rows_csv = _install_ns[
    "run_escalated_delta_operator_metrics_table_rows_csv"
]

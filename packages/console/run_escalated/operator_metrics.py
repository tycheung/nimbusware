from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from console.explainer_core.workflow_metrics_spec import (
    install_workflow_metrics_from_spec,
    repo_display_spec,
)


def _run_escalated_operator_metrics_caption(metrics: Mapping[str, Any] | None) -> str | None:
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


def _noop_caption_parts(_metrics: Mapping[str, Any]) -> list[str]:
    return []


_install_ns: dict[str, object] = {}
install_workflow_metrics_from_spec(
    _install_ns,
    repo_display_spec("run_escalated_latest"),
    caption_parts_fn=_noop_caption_parts,
    custom_caption_fn=_run_escalated_operator_metrics_caption,
)

run_escalated_operator_metrics = _install_ns["run_escalated_operator_metrics"]
run_escalated_operator_metrics_table_rows = _install_ns["run_escalated_operator_metrics_table_rows"]
run_escalated_operator_metrics_caption = _install_ns["run_escalated_operator_metrics_caption"]
run_escalated_operator_metrics_export_json = _install_ns[
    "run_escalated_operator_metrics_export_json"
]
run_escalated_operator_metrics_table_rows_csv = _install_ns[
    "run_escalated_operator_metrics_table_rows_csv"
]

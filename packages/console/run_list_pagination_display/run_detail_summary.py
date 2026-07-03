from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Any

from console.explainer_core.metrics_scaffold import metrics_table_rows
from console.explainer_core.operator_metrics_exports import (
    install_operator_metrics_module,
)
from console.explainer_core.schema_metrics import build_operator_metrics

_DEFAULTS: dict[str, Any] = {
    "event_count": 0,
    "findings_count": 0,
    "has_escalation": False,
    "status_present": False,
    "workflow_profile_present": False,
    "run_id_present": False,
}

_TABLE_ROWS: tuple[tuple[str, str], ...] = (
    ("Event count", "event_count"),
    ("Findings count", "findings_count"),
    ("Has escalation", "has_escalation"),
    ("Status present", "status_present"),
    ("Workflow profile present", "workflow_profile_present"),
    ("Run id present", "run_id_present"),
)


def run_detail_summary_export_json(body: Mapping[str, Any] | None) -> str:
    if not isinstance(body, Mapping):
        return "{}"
    return json.dumps(dict(body), indent=2, ensure_ascii=False)


def run_detail_summary_export_filename_slug(run_id: str, *, max_len: int = 36) -> str:
    raw = str(run_id).strip().lower()
    slug = re.sub(r"[^a-z0-9_.-]+", "_", raw).strip("._-") or "run"
    return slug[:max_len]


def run_detail_summary_operator_metrics(
    body: Mapping[str, Any] | None,
) -> dict[str, Any]:
    metrics = build_operator_metrics(
        body,
        _DEFAULTS,
        int_fields=(("event_count", "event_count"), ("findings_count", "findings_count")),
        bool_fields=(("has_escalation", "has_escalation"),),
        str_present=(
            ("status", "status_present"),
            ("workflow_profile", "workflow_profile_present"),
        ),
    )
    if isinstance(body, Mapping):
        rid = body.get("run_id")
        if rid is None:
            rid = body.get("id")
        metrics["run_id_present"] = isinstance(rid, str) and bool(str(rid).strip())
    return metrics


def run_detail_summary_operator_metrics_table_rows(
    metrics: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    return metrics_table_rows(metrics, _TABLE_ROWS)


def run_detail_summary_operator_metrics_caption(
    metrics: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(metrics, Mapping):
        return None
    if metrics.get("run_id_present") is not True:
        return None
    events = metrics.get("event_count", 0)
    findings = metrics.get("findings_count", 0)
    if not isinstance(events, int) or isinstance(events, bool):
        events = 0
    if not isinstance(findings, int) or isinstance(findings, bool):
        findings = 0
    esc = "yes" if metrics.get("has_escalation") is True else "no"
    return (
        f"Run summary operator metrics: **{events}** event(s), "
        f"**{findings}** finding(s), escalated **{esc}**."
    )


(
    run_detail_summary_operator_metrics,
    run_detail_summary_operator_metrics_table_rows,
    run_detail_summary_operator_metrics_caption,
    run_detail_summary_operator_metrics_export_json,
    run_detail_summary_operator_metrics_table_rows_csv,
    run_detail_summary_operator_metrics_export_filename_slug,
) = install_operator_metrics_module(
    globals(),
    module_prefix="run_detail_summary",
    metrics=run_detail_summary_operator_metrics,
    table_rows=run_detail_summary_operator_metrics_table_rows,
    caption=run_detail_summary_operator_metrics_caption,
    export_slug="run_detail_summary_operator_metrics",
)

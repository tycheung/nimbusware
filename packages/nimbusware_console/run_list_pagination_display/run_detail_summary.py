from __future__ import annotations

import csv
import json
import re
from collections.abc import Mapping, Sequence
from io import StringIO
from typing import Any


def run_detail_summary_export_json(body: Mapping[str, Any] | None) -> str:
    if not isinstance(body, Mapping):
        return "{}"
    return json.dumps(dict(body), indent=2, ensure_ascii=False)


def run_detail_summary_export_filename_slug(run_id: str, *, max_len: int = 36) -> str:
    raw = str(run_id).strip().lower()
    slug = re.sub(r"[^a-z0-9_.-]+", "_", raw).strip("._-") or "run"
    return slug[:max_len]


_RUN_DETAIL_SUMMARY_OPERATOR_METRICS_CSV_COLUMNS: tuple[str, ...] = ("field", "value")


def run_detail_summary_operator_metrics(
    body: Mapping[str, Any] | None,
) -> dict[str, Any]:
    metrics: dict[str, Any] = {
        "event_count": 0,
        "findings_count": 0,
        "has_escalation": False,
        "status_present": False,
        "workflow_profile_present": False,
        "run_id_present": False,
    }
    if not isinstance(body, Mapping):
        return metrics

    def _int_field(key: str) -> int:
        raw = body.get(key)
        if isinstance(raw, int) and not isinstance(raw, bool) and raw >= 0:
            return raw
        return 0

    metrics["event_count"] = _int_field("event_count")
    metrics["findings_count"] = _int_field("findings_count")
    metrics["has_escalation"] = body.get("has_escalation") is True
    status = body.get("status")
    metrics["status_present"] = isinstance(status, str) and bool(status.strip())
    wf = body.get("workflow_profile")
    metrics["workflow_profile_present"] = isinstance(wf, str) and bool(wf.strip())
    rid = body.get("run_id")
    if rid is None:
        rid = body.get("id")
    metrics["run_id_present"] = isinstance(rid, str) and bool(str(rid).strip())
    return metrics


def run_detail_summary_operator_metrics_table_rows(
    metrics: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    if not isinstance(metrics, Mapping):
        return []
    return [
        {"field": "Event count", "value": str(metrics.get("event_count", 0))},
        {"field": "Findings count", "value": str(metrics.get("findings_count", 0))},
        {
            "field": "Has escalation",
            "value": str(metrics.get("has_escalation", False)).lower(),
        },
        {"field": "Status present", "value": str(metrics.get("status_present", False)).lower()},
        {
            "field": "Workflow profile present",
            "value": str(metrics.get("workflow_profile_present", False)).lower(),
        },
        {"field": "Run id present", "value": str(metrics.get("run_id_present", False)).lower()},
    ]


def run_detail_summary_operator_metrics_export_json(
    metrics: Mapping[str, Any] | None,
) -> str:
    if not isinstance(metrics, Mapping):
        return "{}"
    return json.dumps(dict(metrics), indent=2, ensure_ascii=False)


def run_detail_summary_operator_metrics_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_RUN_DETAIL_SUMMARY_OPERATOR_METRICS_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow(
                {k: r.get(k, "") for k in _RUN_DETAIL_SUMMARY_OPERATOR_METRICS_CSV_COLUMNS},
            )
    return buf.getvalue()


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


def run_detail_summary_operator_metrics_export_filename_slug() -> str:
    return "run_detail_summary_operator_metrics"

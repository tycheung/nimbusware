from __future__ import annotations

import csv
import json
import re
from collections.abc import Mapping, Sequence
from io import StringIO
from typing import Any


def run_list_response_pagination_caption(
    data: Mapping[str, Any] | None,
    *,
    link_header_present: bool,
) -> str | None:
    if not isinstance(data, Mapping):
        return None
    raw_ids = data.get("run_ids")
    if not isinstance(raw_ids, list):
        return None
    n = len(raw_ids)
    parts: list[str] = [f"this page: {n} run_id(s)"]
    tot = data.get("total")
    if isinstance(tot, int) and not isinstance(tot, bool):
        parts.append(f"total={tot}")
    hm = data.get("has_more")
    if isinstance(hm, bool):
        parts.append("has_more=yes" if hm else "has_more=no")
    nc = data.get("next_cursor")
    if isinstance(nc, str) and nc.strip():
        parts.append("next_cursor=present")
    else:
        parts.append("next_cursor=absent")
    parts.append("Link header=present" if link_header_present else "Link header=absent")
    off = data.get("offset")
    if isinstance(off, int) and not isinstance(off, bool) and off >= 0:
        parts.append(f"offset={off}")
    lim = data.get("limit")
    if isinstance(lim, int) and not isinstance(lim, bool) and lim >= 1:
        parts.append(f"limit={lim}")
    return "List pagination: " + " · ".join(parts) + "."


def run_list_order_desc_caption(
    params: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(params, Mapping):
        return None
    order = params.get("order")
    if not isinstance(order, str):
        return None
    if order.strip().lower() != "desc":
        return None
    return "List sort order: **desc** (newest first)."


def run_list_has_more_true_caption(data: Mapping[str, Any] | None) -> str | None:
    if not isinstance(data, Mapping):
        return None
    if data.get("has_more") is not True:
        return None
    return (
        "List pagination: **has_more=yes** — use Next (keyset) or Pagination (API) "
        "to fetch another page."
    )


def run_list_pagination_link_caption(*, link_header_present: bool) -> str | None:
    if not link_header_present:
        return None
    return (
        "List API Link header: **present** on the last response "
        "(RFC 5988; see **Pagination (API)** for rel=next)."
    )


def run_list_summaries_sparse_caption(data: Mapping[str, Any] | None) -> str | None:
    if not isinstance(data, Mapping):
        return None
    raw_ids = data.get("run_ids")
    if not isinstance(raw_ids, list) or not raw_ids:
        return None
    summaries = data.get("summaries")
    if not isinstance(summaries, dict):
        return None
    n = len(raw_ids)
    covered = sum(
        1 for rid in raw_ids if isinstance(summaries.get(str(rid)), dict)
    )
    if covered >= n:
        return None
    return (
        f"Sparse ``summaries``: **{covered}** / **{n}** on-page ``run_id``(s) have a summary "
        "object (expand **Raw list JSON** when the API omits rows)."
    )


def run_list_active_query_params_caption(
    params: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(params, Mapping) or not params:
        return (
            "List filters: **defaults only** (no explicit query parameters on the last "
            "list request — see shareable URL below)."
        )
    parts: list[str] = []
    order = params.get("order")
    if order is not None and str(order).strip():
        parts.append(f"order={order}")
    cur = params.get("cursor")
    if isinstance(cur, str) and cur.strip():
        parts.append("cursor=keyset")
    off = params.get("offset")
    if isinstance(off, int) and not isinstance(off, bool) and off > 0:
        parts.append(f"offset={off}")
    lim = params.get("limit")
    if isinstance(lim, int) and not isinstance(lim, bool):
        parts.append(f"limit={lim}")
    stv = params.get("status")
    if stv is not None and str(stv).strip():
        parts.append(f"status={stv}")
    wf = params.get("workflow_profile")
    if wf is not None and str(wf).strip():
        parts.append(f"workflow_profile={wf}")
    pfx = params.get("workflow_profile_prefix")
    if pfx is not None and str(pfx).strip():
        parts.append(f"workflow_profile_prefix={pfx}")
    inc = params.get("include_summary")
    if inc is not None and int(inc) != 0:
        parts.append("include_summary=yes")
    esc = params.get("has_escalation")
    if esc is not None:
        parts.append(f"has_escalation={esc}")
    ca = params.get("created_after")
    if ca is not None and str(ca).strip():
        parts.append("created_after=set")
    cb = params.get("created_before")
    if cb is not None and str(cb).strip():
        parts.append("created_before=set")
    if not parts:
        return None
    return "List filters (last request): " + " · ".join(parts) + "."


def run_list_created_range_caption(
    params: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(params, Mapping):
        return None
    parts: list[str] = []
    ca = params.get("created_after")
    if isinstance(ca, str) and ca.strip():
        parts.append("created_after=set")
    cb = params.get("created_before")
    if isinstance(cb, str) and cb.strip():
        parts.append("created_before=set")
    if not parts:
        return None
    return "List date filter: " + " · ".join(parts) + "."


def run_list_status_filter_caption(
    params: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(params, Mapping):
        return None
    raw = params.get("status")
    if not isinstance(raw, str):
        return None
    text = raw.strip()
    if not text:
        return None
    return f"List status filter: **{text}**."


def run_list_include_summary_filter_caption(
    params: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(params, Mapping):
        return None
    inc = params.get("include_summary")
    if inc is None:
        return None
    try:
        active = int(inc) != 0
    except (TypeError, ValueError):
        return None
    if not active:
        return None
    return "List filter: **include_summary=yes** (per-run summary objects on this page)."


def run_list_workflow_profile_filter_caption(
    params: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(params, Mapping):
        return None
    wf = params.get("workflow_profile")
    if isinstance(wf, str) and wf.strip():
        return f"List workflow filter: profile **`{wf.strip()}`**."
    pfx = params.get("workflow_profile_prefix")
    if isinstance(pfx, str) and pfx.strip():
        return f"List workflow filter: prefix **`{pfx.strip()}`**."
    return None


def run_list_has_escalation_filter_caption(
    params: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(params, Mapping):
        return None
    raw = params.get("has_escalation")
    if raw is None:
        return None
    if isinstance(raw, bool):
        return None
    if not isinstance(raw, int) or isinstance(raw, bool):
        return None
    if raw == 0:
        return "List has_escalation filter: **0** (no escalation)."
    if raw == 1:
        return "List has_escalation filter: **1** (escalation only)."
    return None


def run_list_page_vs_total_caption(data: Mapping[str, Any] | None) -> str | None:
    if not isinstance(data, Mapping):
        return None
    raw_ids = data.get("run_ids")
    if not isinstance(raw_ids, list) or not raw_ids:
        return None
    page_n = len(raw_ids)
    tot = data.get("total")
    if not isinstance(tot, int) or isinstance(tot, bool) or tot < 0:
        return None
    if tot <= page_n:
        return None
    suffix = "run_id" if page_n == 1 else "run_ids"
    return (
        f"List page: **{page_n}** {suffix} on this page of **{tot}** total."
    )


def run_list_keyset_next_page_caption(
    data: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(data, Mapping):
        return None
    hm = data.get("has_more")
    if hm is not True:
        return None
    nc = data.get("next_cursor")
    if not isinstance(nc, str):
        return None
    token = nc.strip()
    if not token:
        return None
    return (
        "List paging: more runs available — use **Next (keyset)** or repeat query "
        "with this page's cursor."
    )


def run_list_next_cursor_length_caption(data: Mapping[str, Any] | None) -> str | None:
    if not isinstance(data, Mapping):
        return None
    nc = data.get("next_cursor")
    if not isinstance(nc, str):
        return None
    token = nc.strip()
    if not token:
        return None
    n = len(token)
    return (
        f"``next_cursor`` opaque token: **{n}** character(s) after trim "
        "(length only; use **Link** / repeat query params to fetch the next page)."
    )


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
                {
                    k: r.get(k, "")
                    for k in _RUN_DETAIL_SUMMARY_OPERATOR_METRICS_CSV_COLUMNS
                },
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


def timeline_events_from_body(body: Mapping[str, Any] | None) -> list[Any]:
    if not isinstance(body, Mapping):
        return []
    raw = body.get("events")
    if not isinstance(raw, list):
        return []
    return raw


def _timeline_event_stringify(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def timeline_events_table_rows(events: Sequence[Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for ev in events:
        if not isinstance(ev, dict):
            continue
        rows.append(
            {
                "event_type": _timeline_event_stringify(ev.get("event_type")),
                "occurred_at": _timeline_event_stringify(ev.get("occurred_at")),
                "event_id": _timeline_event_stringify(ev.get("event_id")),
            },
        )
    return rows


_TIMELINE_EVENTS_CSV_COLUMNS: tuple[str, ...] = ("event_type", "occurred_at", "event_id")


def timeline_events_table_rows_csv(rows: Sequence[Mapping[str, str]]) -> str:
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_TIMELINE_EVENTS_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow({k: r.get(k, "") for k in _TIMELINE_EVENTS_CSV_COLUMNS})
    return buf.getvalue()


def timeline_events_export_json(body: Mapping[str, Any] | None) -> str:
    events = timeline_events_from_body(body)
    return json.dumps(events, indent=2, ensure_ascii=False)


def timeline_events_export_filename_slug(run_id: str, *, max_len: int = 36) -> str:
    return run_detail_summary_export_filename_slug(run_id, max_len=max_len)


def timeline_events_operator_metrics(
    events: Sequence[Any] | None,
) -> dict[str, Any]:
    metrics: dict[str, Any] = {
        "event_count": 0,
        "distinct_event_type_count": 0,
        "top_event_type": None,
        "top_event_type_count": 0,
    }
    if not events:
        return metrics
    type_counts: dict[str, int] = {}
    for ev in events:
        if not isinstance(ev, dict):
            continue
        metrics["event_count"] = int(metrics["event_count"]) + 1
        et = ev.get("event_type")
        if isinstance(et, str) and et.strip():
            key = et.strip()
            type_counts[key] = type_counts.get(key, 0) + 1
    metrics["distinct_event_type_count"] = len(type_counts)
    if type_counts:
        top_type, top_count = max(type_counts.items(), key=lambda x: (x[1], x[0]))
        metrics["top_event_type"] = top_type
        metrics["top_event_type_count"] = top_count
    return metrics


def timeline_events_operator_metrics_table_rows(
    metrics: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    if not isinstance(metrics, Mapping):
        return []
    rows: list[dict[str, str]] = [
        {"field": "Event count", "value": str(metrics.get("event_count", 0))},
        {
            "field": "Distinct event types",
            "value": str(metrics.get("distinct_event_type_count", 0)),
        },
    ]
    top = metrics.get("top_event_type")
    tc = metrics.get("top_event_type_count", 0)
    if isinstance(top, str) and top.strip() and isinstance(tc, int) and not isinstance(tc, bool):
        rows.append({"field": "Top event type", "value": f"{top.strip()} ({tc})"})
    return rows


def timeline_events_operator_metrics_caption(
    metrics: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(metrics, Mapping):
        return None
    ec = metrics.get("event_count")
    if isinstance(ec, bool) or not isinstance(ec, int) or ec < 1:
        return None
    parts = [f"**{ec}** event(s)"]
    det = metrics.get("distinct_event_type_count", 0)
    if isinstance(det, int) and not isinstance(det, bool) and det > 0:
        parts.append(f"**{det}** distinct type(s)")
    top = metrics.get("top_event_type")
    if isinstance(top, str) and top.strip():
        parts.append(f"top type `{top.strip()}`")
    return "Timeline events metrics: " + ", ".join(parts) + "."


_TIMELINE_EVENTS_OPERATOR_METRICS_CSV_COLUMNS: tuple[str, ...] = ("field", "value")


def timeline_events_operator_metrics_export_json(
    metrics: Mapping[str, Any] | None,
) -> str:
    if not isinstance(metrics, Mapping):
        return "{}"
    return json.dumps(dict(metrics), indent=2, ensure_ascii=False)


def timeline_events_operator_metrics_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_TIMELINE_EVENTS_OPERATOR_METRICS_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow(
                {
                    k: r.get(k, "")
                    for k in _TIMELINE_EVENTS_OPERATOR_METRICS_CSV_COLUMNS
                },
            )
    return buf.getvalue()


def timeline_events_operator_metrics_export_filename_slug(
    run_id: str,
    *,
    max_len: int = 36,
) -> str:
    return timeline_events_export_filename_slug(run_id, max_len=max_len)

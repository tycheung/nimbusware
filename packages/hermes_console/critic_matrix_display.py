"""Critic matrix (extracted) for Streamlit (plan §14 #11).

Rows derived from ``critic.verdict.emitted`` events on a timeline ``events`` list.
"""

from __future__ import annotations

import csv
import json
import re
from collections.abc import Mapping, Sequence
from io import StringIO
from typing import Any

_CRITIC_MATRIX_COLUMNS: tuple[str, ...] = (
    "critic_role",
    "verdict",
    "severity",
    "owner_role",
    "event_id",
    "occurred_at",
)


def _stringify(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def critic_matrix_rows_from_events(events: Sequence[Any]) -> list[dict[str, str]]:
    """Extract stable rows from timeline ``events`` (``critic.verdict.emitted`` only)."""
    rows: list[dict[str, str]] = []
    if not isinstance(events, list):
        return rows
    for ev in events:
        if not isinstance(ev, dict):
            continue
        if ev.get("event_type") != "critic.verdict.emitted":
            continue
        pl = ev.get("payload")
        payload = pl if isinstance(pl, dict) else {}
        rows.append(
            {
                "critic_role": _stringify(payload.get("critic_role")),
                "verdict": _stringify(payload.get("verdict")),
                "severity": _stringify(payload.get("severity")),
                "owner_role": _stringify(payload.get("owner_role")),
                "event_id": _stringify(ev.get("event_id")),
                "occurred_at": _stringify(ev.get("occurred_at")),
            },
        )
    return rows


def critic_matrix_operator_metrics(
    rows: Sequence[Mapping[str, str]],
) -> dict[str, Any]:
    """Rollup counts for operator summary."""
    metrics: dict[str, Any] = {
        "verdict_count": 0,
        "fail_count": 0,
        "pass_count": 0,
        "other_verdict_count": 0,
    }
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        metrics["verdict_count"] = int(metrics["verdict_count"]) + 1
        verdict = row.get("verdict")
        if not isinstance(verdict, str):
            metrics["other_verdict_count"] = int(metrics["other_verdict_count"]) + 1
            continue
        key = verdict.strip().upper()
        if key == "FAIL":
            metrics["fail_count"] = int(metrics["fail_count"]) + 1
        elif key == "PASS":
            metrics["pass_count"] = int(metrics["pass_count"]) + 1
        else:
            metrics["other_verdict_count"] = int(metrics["other_verdict_count"]) + 1
    return metrics


def critic_matrix_operator_metrics_table_rows(
    metrics: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    """Two-column rows for ``st.dataframe`` (field / value)."""
    if not isinstance(metrics, Mapping):
        return []
    rows: list[dict[str, str]] = [
        {"field": "Verdict count", "value": str(metrics.get("verdict_count", 0))},
        {"field": "FAIL", "value": str(metrics.get("fail_count", 0))},
        {"field": "PASS", "value": str(metrics.get("pass_count", 0))},
    ]
    other = metrics.get("other_verdict_count", 0)
    if isinstance(other, int) and not isinstance(other, bool) and other > 0:
        rows.append({"field": "Other verdict", "value": str(other)})
    return rows


def critic_matrix_operator_metrics_caption(
    metrics: Mapping[str, Any] | None,
) -> str | None:
    """One-line operator caption when at least one critic verdict exists."""
    if not isinstance(metrics, Mapping):
        return None
    vc = metrics.get("verdict_count")
    if isinstance(vc, bool) or not isinstance(vc, int) or vc < 1:
        return None
    parts = [f"**{vc}** critic verdict(s)"]
    fail = metrics.get("fail_count", 0)
    if isinstance(fail, int) and not isinstance(fail, bool) and fail > 0:
        parts.append(f"**{fail}** FAIL")
    return "Critic matrix: " + ", ".join(parts) + "."


def critic_matrix_export_json(rows: Sequence[Mapping[str, str]]) -> str:
    """Pretty JSON for the critic matrix rows (operator download)."""
    out = [dict(r) for r in rows if isinstance(r, Mapping)]
    return json.dumps(out, indent=2, ensure_ascii=False)


def critic_matrix_table_rows_csv(rows: Sequence[Mapping[str, str]]) -> str:
    """Serialize critic matrix rows to CSV (UTF-8 text)."""
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_CRITIC_MATRIX_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow({k: r.get(k, "") for k in _CRITIC_MATRIX_COLUMNS})
    return buf.getvalue()


def critic_matrix_export_filename_slug(run_id: str, *, max_len: int = 36) -> str:
    """ASCII-ish slug for critic matrix download filenames."""
    raw = str(run_id).strip().lower()
    slug = re.sub(r"[^a-z0-9_.-]+", "_", raw).strip("._-") or "run"
    return slug[:max_len]


_CRITIC_MATRIX_OPERATOR_METRICS_CSV_COLUMNS: tuple[str, ...] = ("field", "value")


def critic_matrix_operator_metrics_export_json(
    metrics: Mapping[str, Any] | None,
) -> str:
    """Pretty JSON for critic matrix operator metrics."""
    if not isinstance(metrics, Mapping):
        return "{}"
    return json.dumps(dict(metrics), indent=2, ensure_ascii=False)


def critic_matrix_operator_metrics_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    """Serialize critic matrix operator metrics rows to CSV."""
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_CRITIC_MATRIX_OPERATOR_METRICS_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow(
                {
                    k: r.get(k, "")
                    for k in _CRITIC_MATRIX_OPERATOR_METRICS_CSV_COLUMNS
                },
            )
    return buf.getvalue()


def critic_matrix_operator_metrics_export_filename_slug(
    run_id: str,
    *,
    max_len: int = 36,
) -> str:
    """ASCII-ish slug for critic matrix operator metrics download filenames."""
    return critic_matrix_export_filename_slug(run_id, max_len=max_len)


_CRITIC_MATRIX_LIVE_COLUMNS: tuple[str, ...] = (
    "stage_name",
    "verdict",
    "status",
    "parallel_group",
    "stage_graph_order_index",
)


def critic_matrix_live_display_caption() -> str:
    return (
        "**Live (orchestration):** gate decisions merged with frozen stage graph "
        "(includes pending critique stages). Distinct from **Extracted (verdict events)** "
        "rows below (`critic.verdict.emitted` only)."
    )


def critic_matrix_live_table_rows(
    rows: Sequence[Mapping[str, Any]] | None,
) -> list[dict[str, str]]:
    """Format live matrix rows for ``st.dataframe``."""
    out: list[dict[str, str]] = []
    if not isinstance(rows, Sequence):
        return out
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        out.append({k: _stringify(row.get(k)) for k in _CRITIC_MATRIX_LIVE_COLUMNS})
    return out


def critic_matrix_live_summary_caption(
    summary: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(summary, Mapping):
        return None
    rc = summary.get("row_count")
    if isinstance(rc, bool) or not isinstance(rc, int) or rc < 1:
        return None
    return (
        f"Live critic matrix: **{rc}** stage row(s) — "
        f"PASS **{summary.get('pass_count', 0)}**, "
        f"FAIL **{summary.get('fail_count', 0)}**, "
        f"pending **{summary.get('pending_count', 0)}**."
        + (
            f" Fail stages: {', '.join(str(x) for x in summary.get('fail_stage_names', []))}."
            if isinstance(summary.get("fail_stage_names"), list)
            and summary.get("fail_stage_names")
            else ""
        )
    )

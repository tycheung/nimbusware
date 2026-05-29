"""Run findings display for Streamlit (plan §14 #11).

Parity with ``GET /v1/runs/{run_id}/findings`` (``finding.created`` events).
"""

from __future__ import annotations

import csv
import json
import re
from collections.abc import Mapping, Sequence
from io import StringIO
from typing import Any

_FINDINGS_TABLE_COLUMNS: tuple[str, ...] = (
    "#",
    "severity",
    "category",
    "owner_role",
    "source_artifact",
    "finding_id",
    "event_id",
    "occurred_at",
)


def _stringify(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def findings_list_from_response(body: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    """Extract ``findings`` from a ``GET /v1/runs/…/findings`` JSON body."""
    if not isinstance(body, Mapping):
        return []
    raw = body.get("findings")
    if not isinstance(raw, list):
        return []
    return [x for x in raw if isinstance(x, dict)]


def findings_table_rows(findings: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    """Rows for ``st.dataframe`` — one row per ``finding.created`` event."""
    rows: list[dict[str, str]] = []
    for i, ev in enumerate(findings, start=1):
        pl = ev.get("payload")
        payload = pl if isinstance(pl, dict) else {}
        rows.append(
            {
                "#": str(i),
                "severity": _stringify(payload.get("severity")),
                "category": _stringify(payload.get("category")),
                "owner_role": _stringify(payload.get("owner_role")),
                "source_artifact": _stringify(payload.get("source_artifact")),
                "finding_id": _stringify(payload.get("finding_id")),
                "event_id": _stringify(ev.get("event_id")),
                "occurred_at": _stringify(ev.get("occurred_at")),
            },
        )
    return rows


def findings_operator_metrics(
    findings: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Rollup counts for operator summary (severity buckets + categories)."""
    metrics: dict[str, Any] = {
        "finding_count": 0,
        "severity_blocker": 0,
        "severity_high": 0,
        "severity_medium": 0,
        "severity_low": 0,
        "severity_other": 0,
        "distinct_categories": 0,
    }
    categories: set[str] = set()
    for ev in findings:
        if not isinstance(ev, Mapping):
            continue
        pl = ev.get("payload")
        payload = pl if isinstance(pl, dict) else {}
        metrics["finding_count"] = int(metrics["finding_count"]) + 1
        sev = payload.get("severity")
        if isinstance(sev, str):
            key = sev.strip().upper()
            if key == "BLOCKER":
                metrics["severity_blocker"] = int(metrics["severity_blocker"]) + 1
            elif key == "HIGH":
                metrics["severity_high"] = int(metrics["severity_high"]) + 1
            elif key == "MEDIUM":
                metrics["severity_medium"] = int(metrics["severity_medium"]) + 1
            elif key == "LOW":
                metrics["severity_low"] = int(metrics["severity_low"]) + 1
            else:
                metrics["severity_other"] = int(metrics["severity_other"]) + 1
        cat = payload.get("category")
        if isinstance(cat, str) and cat.strip():
            categories.add(cat.strip())
    metrics["distinct_categories"] = len(categories)
    return metrics


def findings_operator_metrics_table_rows(
    metrics: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    """Two-column rows for ``st.dataframe`` (field / value)."""
    if not isinstance(metrics, Mapping):
        return []
    rows: list[dict[str, str]] = [
        {"field": "Finding count", "value": str(metrics.get("finding_count", 0))},
        {
            "field": "Distinct categories",
            "value": str(metrics.get("distinct_categories", 0)),
        },
    ]
    for bucket, label in (
        ("severity_blocker", "BLOCKER"),
        ("severity_high", "HIGH"),
        ("severity_medium", "MEDIUM"),
        ("severity_low", "LOW"),
        ("severity_other", "Other severity"),
    ):
        n = metrics.get(bucket, 0)
        if isinstance(n, int) and not isinstance(n, bool) and n > 0:
            rows.append({"field": label, "value": str(n)})
    return rows


def findings_operator_metrics_caption(
    metrics: Mapping[str, Any] | None,
) -> str | None:
    """One-line operator caption when the run has at least one finding."""
    if not isinstance(metrics, Mapping):
        return None
    fc = metrics.get("finding_count")
    if isinstance(fc, bool) or not isinstance(fc, int) or fc < 1:
        return None
    parts = [f"**{fc}** finding(s)"]
    dc = metrics.get("distinct_categories", 0)
    if isinstance(dc, int) and not isinstance(dc, bool):
        parts.append(f"**{dc}** distinct categor{'y' if dc == 1 else 'ies'}")
    for bucket, label in (
        ("severity_blocker", "BLOCKER"),
        ("severity_high", "HIGH"),
        ("severity_medium", "MEDIUM"),
        ("severity_low", "LOW"),
    ):
        n = metrics.get(bucket, 0)
        if isinstance(n, int) and not isinstance(n, bool) and n > 0:
            parts.append(f"**{n}** {label}")
    return "Findings: " + ", ".join(parts) + "."


def findings_empty_caption() -> str:
    """Caption when ``findings`` is empty."""
    return "No finding.created events for this run."


def findings_export_json(body: Mapping[str, Any] | None) -> str:
    """Pretty JSON for the full ``GET …/findings`` response (operator download)."""
    if not isinstance(body, Mapping):
        return "{}"
    return json.dumps(dict(body), indent=2, ensure_ascii=False)


def findings_table_rows_csv(rows: Sequence[Mapping[str, str]]) -> str:
    """Serialize findings table rows to CSV (UTF-8 text)."""
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_FINDINGS_TABLE_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow({k: r.get(k, "") for k in _FINDINGS_TABLE_COLUMNS})
    return buf.getvalue()


def findings_export_filename_slug(run_id: str, *, max_len: int = 36) -> str:
    """ASCII-ish slug for findings download filenames."""
    raw = str(run_id).strip().lower()
    slug = re.sub(r"[^a-z0-9_.-]+", "_", raw).strip("._-") or "run"
    return slug[:max_len]


_FINDINGS_OPERATOR_METRICS_CSV_COLUMNS: tuple[str, ...] = ("field", "value")


def findings_operator_metrics_export_json(
    metrics: Mapping[str, Any] | None,
) -> str:
    """Pretty JSON for findings operator metrics."""
    if not isinstance(metrics, Mapping):
        return "{}"
    return json.dumps(dict(metrics), indent=2, ensure_ascii=False)


def findings_operator_metrics_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    """Serialize findings operator metrics rows to CSV."""
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_FINDINGS_OPERATOR_METRICS_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow(
                {
                    k: r.get(k, "")
                    for k in _FINDINGS_OPERATOR_METRICS_CSV_COLUMNS
                },
            )
    return buf.getvalue()


def findings_operator_metrics_export_filename_slug(
    run_id: str,
    *,
    max_len: int = 36,
) -> str:
    """ASCII-ish slug for findings operator metrics download filenames."""
    return findings_export_filename_slug(run_id, max_len=max_len)

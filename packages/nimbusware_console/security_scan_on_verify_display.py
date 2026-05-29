"""Verifier security-scan snippet summary for Streamlit (plan §14 #18).

Parity with timeline top-level ``security_scan_on_verify`` from the HTTP API.
"""

from __future__ import annotations

import csv
import json
import re
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from io import StringIO
from typing import Any

# Order matches ``security_scan_on_verify_timeline_summary`` in runs (scan first).
_SECURITY_SCAN_ON_VERIFY_FIELDS: tuple[tuple[str, str], ...] = (
    ("security_scan_exit", "Security scan exit"),
    ("security_scan_ruff_exit", "Ruff exit"),
    ("security_scan_bandit_exit", "Bandit exit"),
    ("security_scan_snippet", "Security scan snippet"),
    ("category", "Category"),
    ("severity", "Severity"),
    ("source_artifact", "Source artifact"),
    ("finding_id", "Finding id"),
    ("event_id", "Event id"),
    ("occurred_at", "Occurred at"),
)


def _stringify(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def security_scan_on_verify_from_timeline(
    timeline_body: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    """Return ``security_scan_on_verify`` dict from a ``GET /v1/runs/…/timeline`` JSON body."""
    if not isinstance(timeline_body, Mapping):
        return None
    raw = timeline_body.get("security_scan_on_verify")
    return raw if isinstance(raw, dict) else None


def security_scan_history_from_timeline(
    timeline_body: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    """Return ``security_scan_on_verify_history`` list from a timeline JSON body."""
    if not isinstance(timeline_body, Mapping):
        return []
    raw = timeline_body.get("security_scan_on_verify_history")
    if not isinstance(raw, list):
        return []
    return [x for x in raw if isinstance(x, dict)]


def security_scan_history_table_rows(
    history: list[dict[str, Any]],
) -> list[dict[str, str]]:
    """Rows for ``st.dataframe`` — one row per scan finding in chronological order."""
    rows: list[dict[str, str]] = []
    for i, e in enumerate(history, start=1):
        rows.append(
            {
                "#": str(i),
                "Occurred at": _stringify(e.get("occurred_at")),
                "Severity": _stringify(e.get("severity")),
                "Ruff exit": _stringify(e.get("security_scan_ruff_exit")),
                "Bandit exit": _stringify(e.get("security_scan_bandit_exit")),
                "Scan exit": _stringify(e.get("security_scan_exit")),
                "Finding id": _stringify(e.get("finding_id")),
                "Event id": _stringify(e.get("event_id")),
            },
        )
    return rows


_SECURITY_SCAN_HISTORY_CSV_COLUMNS: tuple[str, ...] = (
    "#",
    "Occurred at",
    "Severity",
    "Ruff exit",
    "Bandit exit",
    "Scan exit",
    "Finding id",
    "Event id",
)


def security_scan_history_table_rows_csv(rows: Sequence[Mapping[str, str]]) -> str:
    """Serialize security scan history display rows to CSV (UTF-8 text)."""
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_SECURITY_SCAN_HISTORY_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow({k: r.get(k, "") for k in _SECURITY_SCAN_HISTORY_CSV_COLUMNS})
    return buf.getvalue()


def security_scan_history_export_json(history: Sequence[Mapping[str, Any]]) -> str:
    """JSON export of raw ``security_scan_on_verify_history`` timeline list."""
    items = [dict(x) for x in history if isinstance(x, Mapping)]
    return json.dumps(items, ensure_ascii=False, indent=2)


def security_scan_history_export_filename_slug(run_id: str, *, max_len: int = 36) -> str:
    """ASCII-ish slug for security scan history download filenames."""
    raw = str(run_id).strip().lower()
    slug = re.sub(r"[^a-z0-9_.-]+", "_", raw).strip("._-") or "run"
    return slug[:max_len]


def security_scan_history_entry_count_caption(
    history: list[dict[str, Any]] | None,
) -> str | None:
    """One-line count of security-scan findings in the bounded timeline history view."""
    if not history:
        return None
    n = len(history)
    word = "finding" if n == 1 else "findings"
    return f"Security scan history: **{n}** {word} in this timeline view."


def security_scan_history_severity_sample_caption(
    history: list[dict[str, Any]] | None,
    *,
    max_n: int = 6,
) -> str | None:
    """One-line sorted sample of distinct severities across scan history entries."""
    if not history or max_n <= 0:
        return None
    severities: set[str] = set()
    for entry in history:
        if not isinstance(entry, dict):
            continue
        sev = entry.get("severity")
        if isinstance(sev, str) and sev.strip():
            severities.add(sev.strip())
    if not severities:
        return None
    ordered = sorted(severities)
    cap = max(1, int(max_n))
    visible = ordered[:cap]
    overflow = len(ordered) - len(visible)
    inner = ", ".join(visible)
    if overflow > 0:
        inner += f" (+{overflow} more)"
    word = "severity" if len(ordered) == 1 else "severities"
    return f"Security scan history distinct {word}: {inner}."


def security_scan_history_operator_metrics(
    history: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    """Rollup counts for operator summary from ``security_scan_on_verify_history``."""
    metrics: dict[str, Any] = {
        "entry_count": 0,
        "distinct_severity_count": 0,
        "severity_sample": [],
        "ruff_nonzero_exit_count": 0,
        "bandit_nonzero_exit_count": 0,
        "failed_scan_exit_count": 0,
    }
    if not history:
        return metrics
    severities: set[str] = set()
    for entry in history:
        if not isinstance(entry, dict):
            continue
        metrics["entry_count"] = int(metrics["entry_count"]) + 1
        sev = entry.get("severity")
        if isinstance(sev, str) and sev.strip():
            severities.add(sev.strip())
        for field, key in (
            ("security_scan_ruff_exit", "ruff_nonzero_exit_count"),
            ("security_scan_bandit_exit", "bandit_nonzero_exit_count"),
            ("security_scan_exit", "failed_scan_exit_count"),
        ):
            val = entry.get(field)
            if isinstance(val, int) and not isinstance(val, bool) and val != 0:
                metrics[key] = int(metrics[key]) + 1
    metrics["distinct_severity_count"] = len(severities)
    metrics["severity_sample"] = sorted(severities)[:5]
    return metrics


def security_scan_history_operator_metrics_table_rows(
    metrics: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    """Two-column rows for ``st.dataframe`` (field / value)."""
    if not isinstance(metrics, Mapping):
        return []
    rows: list[dict[str, str]] = [
        {"field": "Entry count", "value": str(metrics.get("entry_count", 0))},
        {
            "field": "Distinct severities",
            "value": str(metrics.get("distinct_severity_count", 0)),
        },
    ]
    sample = metrics.get("severity_sample")
    if isinstance(sample, list) and sample:
        rows.append(
            {
                "field": "Severity sample",
                "value": ", ".join(str(x) for x in sample if isinstance(x, str)),
            },
        )
    for key, label in (
        ("ruff_nonzero_exit_count", "Ruff non-zero exits"),
        ("bandit_nonzero_exit_count", "Bandit non-zero exits"),
        ("failed_scan_exit_count", "Scan non-zero exits"),
    ):
        n = metrics.get(key, 0)
        if isinstance(n, int) and not isinstance(n, bool) and n > 0:
            rows.append({"field": label, "value": str(n)})
    return rows


def security_scan_history_operator_metrics_caption(
    metrics: Mapping[str, Any] | None,
) -> str | None:
    """One-line operator caption when history has at least one entry."""
    if not isinstance(metrics, Mapping):
        return None
    ec = metrics.get("entry_count")
    if isinstance(ec, bool) or not isinstance(ec, int) or ec < 1:
        return None
    parts = [f"**{ec}** finding(s)"]
    dsc = metrics.get("distinct_severity_count", 0)
    if isinstance(dsc, int) and not isinstance(dsc, bool) and dsc > 0:
        parts.append(f"**{dsc}** distinct severity")
    sample = metrics.get("severity_sample")
    if isinstance(sample, list) and sample:
        visible = [str(x) for x in sample[:3] if isinstance(x, str) and str(x).strip()]
        if visible:
            inner = ", ".join(visible)
            overflow = len(sample) - len(visible)
            if overflow > 0:
                inner += f" (+{overflow} more)"
            parts.append(f"severity sample: {inner}")
    for key, label in (
        ("ruff_nonzero_exit_count", "Ruff failed"),
        ("bandit_nonzero_exit_count", "Bandit failed"),
        ("failed_scan_exit_count", "Scan failed"),
    ):
        n = metrics.get(key, 0)
        if isinstance(n, int) and not isinstance(n, bool) and n > 0:
            parts.append(f"**{n}** {label}")
    return "Security scan history metrics: " + ", ".join(parts) + "."


_SECURITY_SCAN_HISTORY_OPERATOR_METRICS_CSV_COLUMNS: tuple[str, ...] = (
    "field",
    "value",
)


def security_scan_history_operator_metrics_export_json(
    metrics: Mapping[str, Any] | None,
) -> str:
    """Pretty JSON for security scan history operator metrics."""
    if not isinstance(metrics, Mapping):
        return "{}"
    return json.dumps(dict(metrics), indent=2, ensure_ascii=False)


def security_scan_history_operator_metrics_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    """Serialize security scan history operator metrics rows to CSV."""
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_SECURITY_SCAN_HISTORY_OPERATOR_METRICS_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow(
                {
                    k: r.get(k, "")
                    for k in _SECURITY_SCAN_HISTORY_OPERATOR_METRICS_CSV_COLUMNS
                },
            )
    return buf.getvalue()


def security_scan_history_operator_metrics_export_filename_slug(
    run_id: str,
    *,
    max_len: int = 36,
) -> str:
    """ASCII-ish slug for security scan history operator metrics downloads."""
    return security_scan_history_export_filename_slug(run_id, max_len=max_len)


def security_scan_category_severity_caption(
    summary: Mapping[str, Any] | None,
) -> str | None:
    """One-line operator caption for ``category`` / ``severity`` on the timeline summary.

    Emits ``"Security scan finding: category <c>, severity <s>."`` when at least one of
    the two fields is a non-empty string after stripping (order fixed: category then
    severity). Omits a leg entirely when that field is missing, not a string, or
    whitespace-only. Returns ``None`` when ``summary`` is not a mapping or neither leg
    is usable.
    """
    if not isinstance(summary, Mapping):
        return None
    legs: list[str] = []
    cat = summary.get("category")
    if isinstance(cat, str):
        c = cat.strip()
        if c:
            legs.append(f"category {c}")
    sev = summary.get("severity")
    if isinstance(sev, str):
        s = sev.strip()
        if s:
            legs.append(f"severity {s}")
    if not legs:
        return None
    return "Security scan finding: " + ", ".join(legs) + "."


def security_scan_snippet_length_caption(summary: Mapping[str, Any] | None) -> str | None:
    """Operator caption with character length of ``security_scan_snippet`` when present."""
    if not isinstance(summary, Mapping):
        return None
    sn = summary.get("security_scan_snippet")
    if not isinstance(sn, str):
        return None
    stripped = sn.strip()
    if not stripped:
        return None
    return f"Security scan snippet (timeline): **{len(stripped)}** non-whitespace character(s)."


def security_scan_snippet_line_count_caption(summary: Mapping[str, Any] | None) -> str | None:
    """Line count for ``security_scan_snippet`` (newline-separated) when non-empty."""
    if not isinstance(summary, Mapping):
        return None
    sn = summary.get("security_scan_snippet")
    if not isinstance(sn, str):
        return None
    stripped = sn.strip()
    if not stripped:
        return None
    n = len(stripped.splitlines())
    if n < 1:
        return None
    return f"Security scan snippet (timeline): **{n}** line(s)."


def security_scan_finding_event_ids_caption(summary: Mapping[str, Any] | None) -> str | None:
    """Whether ``finding_id`` / ``event_id`` are present as non-empty strings."""
    if not isinstance(summary, Mapping):
        return None
    legs: list[str] = []
    fid = summary.get("finding_id")
    if isinstance(fid, str) and fid.strip():
        legs.append("finding_id present")
    eid = summary.get("event_id")
    if isinstance(eid, str) and eid.strip():
        legs.append("event_id present")
    if not legs:
        return None
    return "Security scan summary: " + ", ".join(legs) + "."


def security_scan_occurred_at_age_caption(summary: Mapping[str, Any] | None) -> str | None:
    """Whole-second age of ``occurred_at`` on the timeline summary vs UTC now."""
    if not isinstance(summary, Mapping):
        return None
    raw = summary.get("occurred_at")
    if not isinstance(raw, str) or not raw.strip():
        return None
    stripped = raw.strip()
    normalised = stripped[:-1] + "+00:00" if stripped.endswith("Z") else stripped
    try:
        parsed = datetime.fromisoformat(normalised)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    age = int((datetime.now(timezone.utc) - parsed).total_seconds())
    if age < 0:
        return None
    return f"Security scan summary **occurred_at** age: **{age}** s (relative to UTC now)."


def security_scan_linter_nonzero_caption(summary: Mapping[str, Any] | None) -> str | None:
    """Short operator hint when Ruff or Bandit subprocess exit codes are non-zero.

    Exit codes are integers on the timeline read-model (``0`` = success). Returns ``None``
    when both are absent, zero, or not integers.
    """
    if not isinstance(summary, Mapping):
        return None
    hints: list[str] = []
    ruff = summary.get("security_scan_ruff_exit")
    if isinstance(ruff, int) and ruff != 0:
        hints.append(f"**Ruff** exit `{ruff}` (non-zero).")
    bandit = summary.get("security_scan_bandit_exit")
    if isinstance(bandit, int) and bandit != 0:
        hints.append(f"**Bandit** exit `{bandit}` (non-zero).")
    if not hints:
        return None
    tail = (
        "Review snippet and finding fields above; cross-check **Security scan metadata on "
        "verify** under Module Integrator (workflow + ``HERMES_ATTACH_SECURITY_SCAN_METADATA``)."
    )
    return " ".join(hints) + " " + tail


_LINTER_EXIT_FIELDS: tuple[tuple[str, str], ...] = (
    ("Ruff", "security_scan_ruff_exit"),
    ("Bandit", "security_scan_bandit_exit"),
)


def security_scan_linter_status_rows(
    summary: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    """Per-linter status rows for ``st.dataframe`` (Ruff / Bandit, in fixed order).

    Each row has ``linter`` / ``exit`` / ``status``. ``status`` is ``ok`` for an integer
    exit code of ``0``, ``failed`` for any other integer, and ``missing`` when the key is
    absent or the value is not an ``int`` (booleans are intentionally treated as missing
    because :class:`bool` is a subclass of :class:`int` and we want only true integers).
    Returns ``[]`` when ``summary`` is not a mapping.
    """
    if not isinstance(summary, Mapping):
        return []
    rows: list[dict[str, str]] = []
    for label, key in _LINTER_EXIT_FIELDS:
        raw = summary.get(key)
        if isinstance(raw, bool) or not isinstance(raw, int):
            rows.append({"linter": label, "exit": "—", "status": "missing"})
            continue
        rows.append(
            {
                "linter": label,
                "exit": str(raw),
                "status": "ok" if raw == 0 else "failed",
            },
        )
    return rows


def security_scan_linter_status_summary_caption(
    summary: Mapping[str, Any] | None,
) -> str | None:
    """One-line operator caption tallying per-linter ``ok`` / ``failed`` / ``missing`` counts.

    Reuses :func:`security_scan_linter_status_rows`. Returns ``None`` when every linter is
    ``missing`` (no signal worth surfacing) or when ``summary`` is not a mapping. Otherwise
    returns a short caption such as ``"Linter summary: 1 ok, 1 failed, 0 missing."``.
    """
    rows = security_scan_linter_status_rows(summary)
    if not rows:
        return None
    tallies = {"ok": 0, "failed": 0, "missing": 0}
    for row in rows:
        status = row.get("status")
        if status in tallies:
            tallies[status] += 1
    if tallies["ok"] == 0 and tallies["failed"] == 0:
        return None
    return (
        "Linter summary: "
        f"{tallies['ok']} ok, "
        f"{tallies['failed']} failed, "
        f"{tallies['missing']} missing."
    )


def security_scan_linter_worst_status_caption(
    summary: Mapping[str, Any] | None,
) -> str | None:
    """Worst-of-linters caption naming the most severe observable Ruff / Bandit status.

    Reuses :func:`security_scan_linter_status_rows`. Severity priority is
    ``failed > ok > missing``. When at least one linter is ``failed``, names the **first**
    failed row in the existing fixed Ruff -> Bandit order and quotes its exit code. When
    every observable linter is ``ok`` (and none are ``failed``), summarises both exits.
    Returns ``None`` when every linter is ``missing`` (no observable signal) or when
    ``summary`` is not a mapping.
    """
    rows = security_scan_linter_status_rows(summary)
    if not rows:
        return None
    failed = [r for r in rows if r.get("status") == "failed"]
    if failed:
        first = failed[0]
        return f"Worst linter: **{first['linter']}** (exit `{first['exit']}`)."
    ok_rows = [r for r in rows if r.get("status") == "ok"]
    if not ok_rows:
        return None
    parts = ", ".join(f"{r['linter']} exit {r['exit']}" for r in ok_rows)
    return f"All linters passed ({parts})."


def security_scan_linter_operator_metrics(
    summary: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Structured per-linter rollup for the **Raw linter operator metrics JSON** expander.

    Reuses :func:`security_scan_linter_status_rows`, so the same Ruff -> Bandit fixed order
    and ``ok`` / ``failed`` / ``missing`` semantics apply. Returns a dict with:

    * ``observable_count`` — count of rows whose ``status`` is ``ok`` or ``failed``.
    * ``ok_count`` / ``failed_count`` / ``missing_count`` — bucket totals.
    * ``worst_status`` — ``"failed"`` if any linter is ``failed``, else ``"ok"`` when at
      least one linter is observably ``ok``, else ``None`` (mirrors the priority used by
      :func:`security_scan_linter_worst_status_caption`).
    * ``worst_linter`` / ``worst_exit`` — the **first** failed row (Ruff -> Bandit) when any
      failed; otherwise ``None`` for both.

    Non-mapping input collapses to all zeros and ``worst_status``/``worst_linter``/
    ``worst_exit`` of ``None``.
    """
    metrics: dict[str, Any] = {
        "observable_count": 0,
        "ok_count": 0,
        "failed_count": 0,
        "missing_count": 0,
        "worst_status": None,
        "worst_linter": None,
        "worst_exit": None,
    }
    rows = security_scan_linter_status_rows(summary)
    if not rows:
        return metrics
    failed_row: dict[str, str] | None = None
    for row in rows:
        status = row.get("status")
        if status == "ok":
            metrics["ok_count"] += 1
        elif status == "failed":
            metrics["failed_count"] += 1
            if failed_row is None:
                failed_row = row
        else:
            metrics["missing_count"] += 1
    metrics["observable_count"] = metrics["ok_count"] + metrics["failed_count"]
    if failed_row is not None:
        metrics["worst_status"] = "failed"
        metrics["worst_linter"] = failed_row["linter"]
        try:
            metrics["worst_exit"] = int(failed_row["exit"])
        except (TypeError, ValueError):
            metrics["worst_exit"] = None
    elif metrics["ok_count"] > 0:
        metrics["worst_status"] = "ok"
    return metrics


def security_scan_linter_operator_metrics_caption(
    metrics: Mapping[str, Any] | None,
) -> str | None:
    """One-line rollup from :func:`security_scan_linter_operator_metrics` output."""
    if not isinstance(metrics, Mapping):
        return None
    if metrics.get("observable_count", 0) == 0:
        return None
    parts = [
        f"observable={metrics['observable_count']}",
        f"ok={metrics.get('ok_count', 0)}",
        f"failed={metrics.get('failed_count', 0)}",
        f"missing={metrics.get('missing_count', 0)}",
    ]
    worst = metrics.get("worst_status")
    if worst == "failed":
        wl = metrics.get("worst_linter")
        we = metrics.get("worst_exit")
        if wl is not None and we is not None:
            parts.append(f"worst={wl} exit {we}")
        else:
            parts.append("worst=failed")
    elif worst == "ok":
        parts.append("worst=all ok")
    return "Linter operator metrics: " + ", ".join(parts) + "."


def security_scan_linter_operator_rollup_caption(
    summary: Mapping[str, Any] | None,
) -> str | None:
    """Compact rollup from :func:`security_scan_linter_operator_metrics`."""
    return security_scan_linter_operator_metrics_caption(
        security_scan_linter_operator_metrics(summary),
    )


def security_scan_linter_ok_linters_caption(
    summary: Mapping[str, Any] | None,
) -> str | None:
    """One-line operator caption naming the linters whose exit code is zero.

    Positive mirror of :func:`security_scan_linter_failed_linters_caption`. Uses
    the same fixed Ruff -> Bandit order from ``_LINTER_EXIT_FIELDS`` and the same
    ``int`` / non-``bool`` observability rule.

    Returns:

    * ``"Passing linter: Ruff."`` / ``"Passing linter: Bandit."`` when exactly one
      observable linter reports exit ``0``,
    * ``"Passing linters: Ruff, Bandit."`` when both observable linters report
      exit ``0``,
    * ``None`` when ``summary`` is not a mapping, when no linter is observable, or
      when every observable linter has a non-zero exit.

    Purely additive — does **not** replace ``security_scan_linter_worst_status_caption``
    (whose "All linters passed (...)." line already covers the all-ok summary tally).
    """
    if not isinstance(summary, Mapping):
        return None
    passing: list[str] = []
    for label, key in _LINTER_EXIT_FIELDS:
        raw = summary.get(key)
        if isinstance(raw, bool) or not isinstance(raw, int):
            continue
        if raw == 0:
            passing.append(label)
    if not passing:
        return None
    if len(passing) == 1:
        return f"Passing linter: {passing[0]}."
    return "Passing linters: " + ", ".join(passing) + "."


def security_scan_linter_missing_linters_caption(
    summary: Mapping[str, Any] | None,
) -> str | None:
    """One-line operator caption naming the linters with no integer exit on the timeline.

    Third member of the ok / failed / **missing** caption trio. A linter is **missing**
    when :func:`security_scan_linter_status_rows` would emit ``status: missing`` for it
    (key absent, value not an ``int``, or value is a ``bool`` — booleans are excluded
    because :class:`bool` subclasses :class:`int`).

    Returns ``"Missing linter: Ruff."`` / ``"Missing linter: Bandit."`` when exactly one
    linter is missing, ``"Missing linters: Ruff, Bandit."`` when both are missing, and
    ``None`` when ``summary`` is not a mapping or when **both** linters are observable
    (regardless of pass/fail).
    """
    if not isinstance(summary, Mapping):
        return None
    missing: list[str] = []
    for label, key in _LINTER_EXIT_FIELDS:
        raw = summary.get(key)
        if isinstance(raw, bool) or not isinstance(raw, int):
            missing.append(label)
    if not missing:
        return None
    if len(missing) == 1:
        return f"Missing linter: {missing[0]}."
    return "Missing linters: " + ", ".join(missing) + "."


def security_scan_linter_failed_linters_caption(
    summary: Mapping[str, Any] | None,
) -> str | None:
    """One-line operator caption naming the linters whose exit code is non-zero.

    Mirrors the observability rule used by :func:`security_scan_linter_status_rows`
    (entry observable only when ``summary[key]`` is an ``int`` and **not** a ``bool``)
    and the fixed Ruff -> Bandit order shared with
    :func:`security_scan_linter_worst_status_caption`.

    Returns:

    * ``"Failed linter: Ruff."`` / ``"Failed linter: Bandit."`` when exactly one
      observable linter has a non-zero exit code,
    * ``"Failed linters: Ruff, Bandit."`` when both observable linters failed,
    * ``None`` when ``summary`` is not a mapping, when no linter is observable, or
      when every observable linter reported an exit code of ``0``.

    Purely additive — does **not** replace ``security_scan_linter_worst_status_caption``.
    """
    if not isinstance(summary, Mapping):
        return None
    failed: list[str] = []
    for label, key in _LINTER_EXIT_FIELDS:
        raw = summary.get(key)
        if isinstance(raw, bool) or not isinstance(raw, int):
            continue
        if raw != 0:
            failed.append(label)
    if not failed:
        return None
    if len(failed) == 1:
        return f"Failed linter: {failed[0]}."
    return "Failed linters: " + ", ".join(failed) + "."


def security_scan_linter_exit_codes_caption(
    summary: Mapping[str, Any] | None,
) -> str | None:
    """One-line operator caption listing the per-linter exit codes observed.

    Mirrors the observability rule used by :func:`security_scan_linter_status_rows`:
    an entry is observable only when ``summary[key]`` is an ``int`` and **not** a
    ``bool`` (``bool`` is a subclass of :class:`int` and we want only true integers).

    Returns:

    * ``"Linter exit codes: Ruff=<n>, Bandit=<m>."`` when both linters are observable,
    * ``"Linter exit codes: Ruff=<n>."`` / ``"Linter exit codes: Bandit=<m>."`` when
      only one is observable,
    * ``None`` when ``summary`` is not a mapping or neither linter is observable.
    """
    if not isinstance(summary, Mapping):
        return None
    observed: list[str] = []
    for label, key in _LINTER_EXIT_FIELDS:
        raw = summary.get(key)
        if isinstance(raw, bool) or not isinstance(raw, int):
            continue
        observed.append(f"{label}={raw}")
    if not observed:
        return None
    return "Linter exit codes: " + ", ".join(observed) + "."


def security_scan_linter_operator_metrics_table_rows(
    metrics: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    """Two-column ``field`` / ``value`` rows for the linter operator metrics dict.

    Renders the dict returned by :func:`security_scan_linter_operator_metrics` as stable
    ``st.dataframe`` rows, mirroring ``self_refinement_timeline_metrics_table_rows``.
    Always emits the four bucket counts (``Observable linters`` / ``Ok`` / ``Failed`` /
    ``Missing``); appends ``Worst status`` / ``Worst linter`` / ``Worst exit`` rows only
    when ``worst_status`` is not ``None`` (so a fully missing signal collapses to the
    four bucket counts and nothing else).

    Returns ``[]`` when ``metrics`` is not a mapping or is empty.
    """
    if not isinstance(metrics, Mapping) or not metrics:
        return []
    rows: list[dict[str, str]] = [
        {"field": "Observable linters", "value": str(metrics.get("observable_count", 0))},
        {"field": "Ok", "value": str(metrics.get("ok_count", 0))},
        {"field": "Failed", "value": str(metrics.get("failed_count", 0))},
        {"field": "Missing", "value": str(metrics.get("missing_count", 0))},
    ]
    worst_status = metrics.get("worst_status")
    if worst_status is None:
        return rows
    rows.append({"field": "Worst status", "value": str(worst_status)})
    worst_linter = metrics.get("worst_linter")
    if worst_linter is not None:
        rows.append({"field": "Worst linter", "value": str(worst_linter)})
    worst_exit = metrics.get("worst_exit")
    if worst_exit is not None:
        rows.append({"field": "Worst exit", "value": str(worst_exit)})
    return rows


def security_scan_on_verify_summary_rows(
    summary: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    """Rows suitable for ``st.dataframe`` (field / value columns)."""
    if not summary:
        return []
    rows: list[dict[str, str]] = []
    for key, label in _SECURITY_SCAN_ON_VERIFY_FIELDS:
        if key not in summary:
            continue
        rows.append({"field": label, "value": _stringify(summary.get(key))})
    return rows


_SECURITY_SCAN_ON_VERIFY_LATEST_SUMMARY_CSV_COLUMNS: tuple[str, ...] = ("field", "value")


def security_scan_on_verify_latest_summary_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    """Serialize latest security_scan_on_verify summary rows to CSV (UTF-8 text)."""
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_SECURITY_SCAN_ON_VERIFY_LATEST_SUMMARY_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow(
                {k: r.get(k, "") for k in _SECURITY_SCAN_ON_VERIFY_LATEST_SUMMARY_CSV_COLUMNS},
            )
    return buf.getvalue()


def security_scan_on_verify_latest_export_json(
    summary: Mapping[str, Any] | None,
) -> str:
    """JSON export of timeline top-level ``security_scan_on_verify`` summary."""
    if not isinstance(summary, Mapping):
        return "{}"
    return json.dumps(dict(summary), ensure_ascii=False, indent=2)


def security_scan_on_verify_latest_export_filename_slug(
    run_id: str,
    *,
    max_len: int = 36,
) -> str:
    """ASCII-ish slug for latest security_scan_on_verify download filenames."""
    raw = str(run_id).strip().lower()
    slug = re.sub(r"[^a-z0-9_.-]+", "_", raw).strip("._-") or "run"
    return slug[:max_len]


def _security_scan_snippet_char_len(summary: Mapping[str, Any]) -> int:
    sn = summary.get("security_scan_snippet")
    if not isinstance(sn, str):
        return 0
    return len(sn.strip())


def security_scan_on_verify_latest_operator_metrics(
    summary: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Rollup for latest timeline ``security_scan_on_verify`` finding summary."""
    metrics: dict[str, Any] = {
        "category_present": False,
        "severity_present": False,
        "snippet_char_len": 0,
        "finding_id_present": False,
        "event_id_present": False,
        "security_scan_ruff_exit": None,
        "security_scan_bandit_exit": None,
    }
    if not isinstance(summary, Mapping):
        return metrics
    cat = summary.get("category")
    metrics["category_present"] = isinstance(cat, str) and bool(cat.strip())
    sev = summary.get("severity")
    metrics["severity_present"] = isinstance(sev, str) and bool(sev.strip())
    metrics["snippet_char_len"] = _security_scan_snippet_char_len(summary)
    fid = summary.get("finding_id")
    metrics["finding_id_present"] = isinstance(fid, str) and bool(fid.strip())
    eid = summary.get("event_id")
    metrics["event_id_present"] = isinstance(eid, str) and bool(eid.strip())
    for key in ("security_scan_ruff_exit", "security_scan_bandit_exit"):
        val = summary.get(key)
        if isinstance(val, int) and not isinstance(val, bool):
            metrics[key] = int(val)
    return metrics


def security_scan_on_verify_latest_operator_metrics_table_rows(
    metrics: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    """Two-column rows for ``st.dataframe`` (field / value)."""
    if not isinstance(metrics, Mapping):
        return []
    rows: list[dict[str, str]] = []
    if metrics.get("category_present") is True:
        rows.append({"field": "Category present", "value": "yes"})
    if metrics.get("severity_present") is True:
        rows.append({"field": "Severity present", "value": "yes"})
    scl = metrics.get("snippet_char_len", 0)
    if isinstance(scl, int) and not isinstance(scl, bool) and scl > 0:
        rows.append({"field": "Snippet length (chars)", "value": str(scl)})
    if metrics.get("finding_id_present") is True:
        rows.append({"field": "Finding id present", "value": "yes"})
    if metrics.get("event_id_present") is True:
        rows.append({"field": "Event id present", "value": "yes"})
    for key, label in (
        ("security_scan_ruff_exit", "Ruff exit code"),
        ("security_scan_bandit_exit", "Bandit exit code"),
    ):
        val = metrics.get(key)
        if isinstance(val, int) and not isinstance(val, bool):
            rows.append({"field": label, "value": str(val)})
    return rows


def security_scan_on_verify_latest_operator_metrics_caption(
    metrics: Mapping[str, Any] | None,
) -> str | None:
    """One-line operator caption from latest security scan finding rollup."""
    if not isinstance(metrics, Mapping):
        return None
    parts: list[str] = []
    if metrics.get("category_present") is True:
        parts.append("category")
    if metrics.get("severity_present") is True:
        parts.append("severity")
    scl = metrics.get("snippet_char_len", 0)
    if isinstance(scl, int) and not isinstance(scl, bool) and scl > 0:
        parts.append(f"**{scl}**-char snippet")
    if metrics.get("finding_id_present") is True:
        parts.append("finding id")
    ruff = metrics.get("security_scan_ruff_exit")
    if isinstance(ruff, int) and not isinstance(ruff, bool):
        parts.append(f"ruff_exit={ruff}")
    bandit = metrics.get("security_scan_bandit_exit")
    if isinstance(bandit, int) and not isinstance(bandit, bool):
        parts.append(f"bandit_exit={bandit}")
    if not parts:
        return None
    return "Security scan finding metrics: " + ", ".join(parts) + "."


_SECURITY_SCAN_ON_VERIFY_LATEST_OPERATOR_METRICS_CSV_COLUMNS: tuple[str, ...] = (
    "field",
    "value",
)


def security_scan_on_verify_latest_operator_metrics_export_json(
    metrics: Mapping[str, Any] | None,
) -> str:
    """Pretty JSON for latest security scan finding operator metrics."""
    if not isinstance(metrics, Mapping):
        return "{}"
    return json.dumps(dict(metrics), indent=2, ensure_ascii=False)


def security_scan_on_verify_latest_operator_metrics_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    """Serialize latest security scan finding operator metrics rows to CSV."""
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_SECURITY_SCAN_ON_VERIFY_LATEST_OPERATOR_METRICS_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow(
                {
                    k: r.get(k, "")
                    for k in _SECURITY_SCAN_ON_VERIFY_LATEST_OPERATOR_METRICS_CSV_COLUMNS
                },
            )
    return buf.getvalue()


def security_scan_on_verify_latest_operator_metrics_export_filename_slug(
    run_id: str,
    *,
    max_len: int = 36,
) -> str:
    """ASCII-ish slug for latest security scan finding operator metrics downloads."""
    return security_scan_on_verify_latest_export_filename_slug(run_id, max_len=max_len)


_SECURITY_SCAN_LINTER_METRICS_CSV_COLUMNS: tuple[str, ...] = ("field", "value")


def security_scan_linter_operator_metrics_export_json(
    metrics: Mapping[str, Any] | None,
) -> str:
    """Pretty JSON for security-scan linter operator metrics."""
    if not isinstance(metrics, Mapping):
        return "{}"
    return json.dumps(dict(metrics), indent=2, ensure_ascii=False)


def security_scan_linter_operator_metrics_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    """Serialize security-scan linter operator metrics rows to CSV."""
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_SECURITY_SCAN_LINTER_METRICS_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow(
                {
                    k: r.get(k, "")
                    for k in _SECURITY_SCAN_LINTER_METRICS_CSV_COLUMNS
                },
            )
    return buf.getvalue()


def security_scan_linter_operator_metrics_export_filename_slug(
    run_id: str,
    *,
    max_len: int = 36,
) -> str:
    """ASCII-ish slug for security-scan linter operator metrics downloads."""
    return security_scan_on_verify_latest_export_filename_slug(run_id, max_len=max_len)


def security_scan_metadata_timeline_workflow_alignment_caption(
    *,
    timeline_security_scan_on_verify: Mapping[str, Any] | None,
    explainer_payload: Mapping[str, Any] | None,
) -> str | None:
    """Compare timeline **security_scan_on_verify** vs Module Integrator ``effective_enabled``.

    Uses :func:`security_scan_on_verify_summary_rows` to detect operator-visible scan output
    on the timeline. Returns ``None`` when the explainer payload is missing, carries a
    non-empty ``load_error``, lacks a strict-bool ``effective_enabled``, or the signals
    already align (scan output present ↔ effective true, or both absent/off).
    """
    if not isinstance(explainer_payload, Mapping):
        return None
    err = explainer_payload.get("load_error")
    if isinstance(err, str) and err.strip():
        return None
    eff = explainer_payload.get("effective_enabled")
    if not isinstance(eff, bool):
        return None
    has_scan = bool(security_scan_on_verify_summary_rows(timeline_security_scan_on_verify))
    if has_scan and not eff:
        return (
            "Timeline shows **security_scan_on_verify** scan output, but "
            "**security_scan_metadata_on_verify** is **effective false** for the selected "
            "workflow profile (YAML + ``HERMES_ATTACH_SECURITY_SCAN_METADATA``). "
            "Cross-check **Module Integrator** > Security scan metadata on verify."
        )
    if (not has_scan) and eff:
        return (
            "Workflow enables **security_scan_metadata_on_verify** for the selected profile, "
            "but this timeline has no **security_scan_on_verify** summary (no verifier scan "
            "metadata on finding.created events yet)."
        )
    return None

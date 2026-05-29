"""Preflight history summary for Streamlit (plan §14 #11.

Parity with the timeline top-level ``preflight`` summary from the HTTP API
(:func:`nimbusware_api.preflight_read_model.preflight_timeline_summary`). Three pure
functions:

* :func:`preflight_history_from_timeline` — extract the ``preflight`` dict from
 a ``GET /v1/runs/{run_id}/timeline`` body.
* :func:`preflight_history_summary_rows` — turn that dict into field/value
 rows for ``st.dataframe``.
* :func:`preflight_history_histogram_payload` — build the latency histogram
 for the Streamlit bar chart, with graceful fallback when raw per-sample
 data is missing (runs where ``health_latency_samples_ms`` was never recorded).

All functions are side-effect-free so they can be unit-tested without
spinning up Streamlit.
"""

from __future__ import annotations

import csv
import json
import re
from collections.abc import Mapping, Sequence
from io import StringIO
from typing import Any

from hermes_orchestrator.preflight_histogram import build_histogram, empty_histogram

# Order mirrors the operator-readable layout of the rendered table; the API
# helper ``preflight_timeline_summary`` returns these keys (and may return
# ``None`` values when those keys were omitted from the preflight projection).
_PREFLIGHT_FIELDS: tuple[tuple[str, str], ...] = (
    ("validated_model_id", "Validated model id"),
    ("provider", "Provider"),
    ("context_tokens", "Context tokens"),
    ("p95_latency_ms", "p95 latency (ms)"),
    ("preflight_latency_sample_count", "Samples used"),
    ("p95_latency_source", "p95 source"),
    ("checks_passed", "Checks passed"),
    ("event_id", "Event id"),
    ("occurred_at", "Occurred at"),
)


def _stringify(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def preflight_history_from_timeline(
    timeline_body: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    """Return the ``preflight`` dict from a ``GET /v1/runs/…/timeline`` JSON body.

    Defensive: returns ``None`` for any non-mapping input or when the top-level
    key is missing / not a dict (matches the convention used by the sibling
    ``*_from_timeline`` helpers like
    :mod:`nimbusware_console.security_scan_on_verify_display`).
    """
    if not isinstance(timeline_body, Mapping):
        return None
    raw = timeline_body.get("preflight")
    return raw if isinstance(raw, dict) else None


def preflight_history_summary_rows(
    summary: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    """Rows for ``st.dataframe`` (field / value columns).

    Omits keys that are absent from ``summary`` (so rows without
    ``health_latency_samples_ms`` do not add a field) but RENDERS
    keys whose value is ``None`` as ``—`` since the operator should still see
    that the field was projected. Returns ``[]`` when ``summary`` is falsy so
    the Streamlit caller can show a neutral caption instead of an empty table.
    """
    if not summary:
        return []
    rows: list[dict[str, str]] = []
    for key, label in _PREFLIGHT_FIELDS:
        if key not in summary:
            continue
        rows.append({"field": label, "value": _stringify(summary.get(key))})
    return rows


_PREFLIGHT_SUMMARY_CSV_COLUMNS: tuple[str, ...] = ("field", "value")


def preflight_history_summary_rows_csv(rows: Sequence[Mapping[str, str]]) -> str:
    """Serialize preflight summary field/value rows to CSV (UTF-8 text)."""
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_PREFLIGHT_SUMMARY_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow({k: r.get(k, "") for k in _PREFLIGHT_SUMMARY_CSV_COLUMNS})
    return buf.getvalue()


def preflight_history_export_json(summary: Mapping[str, Any] | None) -> str:
    """Pretty JSON export of timeline ``preflight`` summary."""
    if not isinstance(summary, Mapping):
        return "{}"
    return json.dumps(dict(summary), ensure_ascii=False, indent=2)


def preflight_history_export_filename_slug(run_id: str, *, max_len: int = 36) -> str:
    """ASCII-ish slug for preflight timeline download filenames."""
    raw = str(run_id).strip().lower()
    slug = re.sub(r"[^a-z0-9_.-]+", "_", raw).strip("._-") or "run"
    return slug[:max_len]


def preflight_history_histogram_mode_caption(
    summary: Mapping[str, Any] | None,
) -> str | None:
    """Distinguish multisample histogram vs legacy single-bar p95 fallback (§14 #1)."""
    if not summary:
        return None
    raw_samples = summary.get("health_latency_samples_ms")
    if isinstance(raw_samples, list) and raw_samples:
        samples = [
            int(s) for s in raw_samples if isinstance(s, int) and not isinstance(s, bool)
        ]
        if samples:
            n = len(samples)
            sc = summary.get("preflight_latency_sample_count")
            tail = ""
            if isinstance(sc, int) and not isinstance(sc, bool):
                tail = f" Persisted sample_count={sc}."
            return (
                f"Histogram: **{n}** health latency sample(s) from timeline.{tail}"
            )
    p95 = summary.get("p95_latency_ms")
    if isinstance(p95, int) and not isinstance(p95, bool) and p95 >= 0:
        return (
            "Histogram: **legacy single-bar** fallback from p95_latency_ms only "
            "(no health_latency_samples_ms on this event)."
        )
    return None


def preflight_history_event_id_caption(
    summary: Mapping[str, Any] | None,
) -> str | None:
    """Surface timeline ``event_id`` on the per-run preflight summary."""
    if not isinstance(summary, Mapping):
        return None
    raw = summary.get("event_id")
    if not isinstance(raw, str):
        return None
    text = raw.strip()
    if not text:
        return None
    return f"Preflight event id: `{text}`."


def preflight_history_p95_latency_caption(
    summary: Mapping[str, Any] | None,
) -> str | None:
    """One-line ``p95_latency_ms`` from the timeline preflight summary."""
    if not isinstance(summary, Mapping):
        return None
    raw = summary.get("p95_latency_ms")
    if not isinstance(raw, int) or isinstance(raw, bool) or raw < 0:
        return None
    return f"Preflight p95 latency: **{raw}** ms."


def preflight_history_p95_source_caption(
    summary: Mapping[str, Any] | None,
) -> str | None:
    """One-line caption for how ``p95_latency_ms`` was derived on the timeline row."""
    if not summary:
        return None
    src = summary.get("p95_latency_source")
    if not isinstance(src, str):
        return None
    text = src.strip()
    if not text:
        return None
    return f"Preflight p95 source: **{text}**."


def preflight_history_provider_caption(
    summary: Mapping[str, Any] | None,
) -> str | None:
    """Surface timeline ``provider`` on the per-run preflight summary."""
    if not summary:
        return None
    raw = summary.get("provider")
    if not isinstance(raw, str):
        return None
    text = raw.strip()
    if not text:
        return None
    return f"Preflight provider: **{text}**."


def preflight_history_validated_model_caption(
    summary: Mapping[str, Any] | None,
) -> str | None:
    """Surface timeline ``validated_model_id`` on the per-run preflight summary."""
    if not summary:
        return None
    raw = summary.get("validated_model_id")
    if not isinstance(raw, str):
        return None
    text = raw.strip()
    if not text:
        return None
    return f"Preflight validated model: `{text}`."


def preflight_history_sample_count_caption(
    summary: Mapping[str, Any] | None,
) -> str | None:
    """One-line ``preflight_latency_sample_count`` from the timeline preflight summary."""
    if not summary:
        return None
    raw = summary.get("preflight_latency_sample_count")
    if not isinstance(raw, int) or isinstance(raw, bool) or raw <= 0:
        return None
    word = "sample" if raw == 1 else "samples"
    return f"Preflight latency {word}: **{raw}**."


def preflight_history_context_tokens_caption(
    summary: Mapping[str, Any] | None,
) -> str | None:
    """One-line ``context_tokens`` from the timeline preflight summary."""
    if not summary:
        return None
    raw = summary.get("context_tokens")
    if not isinstance(raw, int) or isinstance(raw, bool) or raw <= 0:
        return None
    return f"Preflight context tokens: **{raw}**."


def preflight_history_checks_passed_caption(
    summary: Mapping[str, Any] | None,
    *,
    max_sample: int = 4,
) -> str | None:
    """Count and sample timeline ``checks_passed`` strings."""
    if not summary:
        return None
    raw = summary.get("checks_passed")
    if not isinstance(raw, list) or not raw:
        return None
    names = sorted(
        {str(x).strip() for x in raw if isinstance(x, str) and str(x).strip()},
    )
    if not names:
        return None
    n = len(names)
    sample = names[:max_sample]
    body = ", ".join(sample)
    if n > max_sample:
        body = f"{body}, +{n - max_sample} more"
    return f"Preflight checks passed ({n}): {body}."


def preflight_history_latency_samples_table_rows(
    summary: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    """Per-sample latency rows from ``health_latency_samples_ms`` (§14 #11)."""
    if not isinstance(summary, Mapping):
        return []
    raw = summary.get("health_latency_samples_ms")
    if not isinstance(raw, list) or not raw:
        return []
    rows: list[dict[str, str]] = []
    for i, sample in enumerate(raw, start=1):
        if isinstance(sample, bool) or not isinstance(sample, int):
            continue
        rows.append({"#": str(i), "Latency ms": str(sample)})
    return rows


def preflight_history_samples_table_caption(
    summary: Mapping[str, Any] | None,
) -> str | None:
    """Caption when multisample preflight exposes two or more latency samples."""
    rows = preflight_history_latency_samples_table_rows(summary)
    if len(rows) < 2:
        return None
    return f"Preflight latency samples: **{len(rows)}** row(s) from timeline."


def preflight_history_histogram_payload(
    summary: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    """Return a histogram payload suitable for ``st.bar_chart`` rendering.

    Three branches:

    * ``summary`` is falsy → return ``None`` so the caller can hide the chart.
    * ``health_latency_samples_ms`` is a non-empty list → call shared
      :func:`build_histogram` over the integer samples.
    * Otherwise → fall back to a synthetic single-sample histogram using
      ``p95_latency_ms`` (only emits a bar when p95 is a non-negative int).
      Legacy events that predate the fo124 payload extension flow through
      this branch.

    The shape returned is always either the shared ``build_histogram`` payload
    (with ``count``, ``buckets``, ``samples_ms``, …) or :func:`empty_histogram`,
    so the caller can always read ``payload["count"]`` and ``payload["buckets"]``
    without ``None``-checking past this function.
    """
    if not summary:
        return None
    raw_samples = summary.get("health_latency_samples_ms")
    if isinstance(raw_samples, list) and raw_samples:
        samples = [int(s) for s in raw_samples if isinstance(s, int) and not isinstance(s, bool)]
        if samples:
            return build_histogram(samples)
    p95 = summary.get("p95_latency_ms")
    if isinstance(p95, int) and not isinstance(p95, bool) and p95 >= 0:
        return build_histogram([p95])
    return empty_histogram()


def preflight_history_operator_metrics(
    summary: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Rollup counts for operator summary from timeline ``preflight``."""
    metrics: dict[str, Any] = {
        "has_p95_latency": False,
        "sample_count": 0,
        "multisample": False,
        "checks_passed_count": 0,
        "health_latency_samples_count": 0,
        "validated_model_present": False,
    }
    if not isinstance(summary, Mapping):
        return metrics
    p95 = summary.get("p95_latency_ms")
    metrics["has_p95_latency"] = (
        isinstance(p95, int) and not isinstance(p95, bool) and p95 >= 0
    )
    sc = summary.get("preflight_latency_sample_count")
    if isinstance(sc, int) and not isinstance(sc, bool):
        metrics["sample_count"] = sc
        metrics["multisample"] = sc > 1
    raw_checks = summary.get("checks_passed")
    if isinstance(raw_checks, list):
        metrics["checks_passed_count"] = sum(
            1 for item in raw_checks if isinstance(item, str) and item.strip()
        )
    raw_samples = summary.get("health_latency_samples_ms")
    if isinstance(raw_samples, list):
        metrics["health_latency_samples_count"] = sum(
            1
            for s in raw_samples
            if isinstance(s, int) and not isinstance(s, bool)
        )
    vm = summary.get("validated_model_id")
    metrics["validated_model_present"] = vm is not None and str(vm).strip() != ""
    return metrics


def preflight_history_operator_metrics_table_rows(
    metrics: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    """Two-column rows for ``st.dataframe`` (field / value)."""
    if not isinstance(metrics, Mapping):
        return []
    rows: list[dict[str, str]] = []
    if metrics.get("has_p95_latency") is True:
        rows.append({"field": "Has p95 latency", "value": "yes"})
    sc = metrics.get("sample_count", 0)
    if isinstance(sc, int) and not isinstance(sc, bool) and sc > 0:
        rows.append({"field": "Sample count", "value": str(sc)})
    if metrics.get("multisample") is True:
        rows.append({"field": "Multisample", "value": "yes"})
    cpc = metrics.get("checks_passed_count", 0)
    if isinstance(cpc, int) and not isinstance(cpc, bool) and cpc > 0:
        rows.append({"field": "Checks passed count", "value": str(cpc)})
    hlc = metrics.get("health_latency_samples_count", 0)
    if isinstance(hlc, int) and not isinstance(hlc, bool) and hlc > 0:
        rows.append({"field": "Health latency samples", "value": str(hlc)})
    if metrics.get("validated_model_present") is True:
        rows.append({"field": "Validated model present", "value": "yes"})
    return rows


def preflight_history_operator_metrics_caption(
    metrics: Mapping[str, Any] | None,
) -> str | None:
    """One-line operator caption from preflight rollup metrics."""
    if not isinstance(metrics, Mapping):
        return None
    parts: list[str] = []
    if metrics.get("has_p95_latency") is True:
        parts.append("p95 present")
    sc = metrics.get("sample_count", 0)
    if isinstance(sc, int) and not isinstance(sc, bool) and sc > 0:
        parts.append(f"**{sc}** sample(s)")
    if metrics.get("multisample") is True:
        parts.append("multisample")
    cpc = metrics.get("checks_passed_count", 0)
    if isinstance(cpc, int) and not isinstance(cpc, bool) and cpc > 0:
        parts.append(f"**{cpc}** check(s) passed")
    if metrics.get("validated_model_present") is True:
        parts.append("validated model")
    if not parts:
        return None
    return "Preflight history metrics: " + ", ".join(parts) + "."


_PREFLIGHT_HISTORY_OPERATOR_METRICS_CSV_COLUMNS: tuple[str, ...] = (
    "field",
    "value",
)


def preflight_history_operator_metrics_export_json(
    metrics: Mapping[str, Any] | None,
) -> str:
    """Pretty JSON for preflight history operator metrics."""
    if not isinstance(metrics, Mapping):
        return "{}"
    return json.dumps(dict(metrics), indent=2, ensure_ascii=False)


def preflight_history_operator_metrics_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    """Serialize preflight history operator metrics rows to CSV."""
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_PREFLIGHT_HISTORY_OPERATOR_METRICS_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow(
                {
                    k: r.get(k, "")
                    for k in _PREFLIGHT_HISTORY_OPERATOR_METRICS_CSV_COLUMNS
                },
            )
    return buf.getvalue()


def preflight_history_operator_metrics_export_filename_slug(
    run_id: str,
    *,
    max_len: int = 36,
) -> str:
    """ASCII-ish slug for preflight history operator metrics downloads."""
    return preflight_history_export_filename_slug(run_id, max_len=max_len)

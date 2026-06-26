from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

from agent_core.coercion import is_strict_int
from nimbusware_console.components.operator_metrics import mapping_export_json
from nimbusware_console.explainer_core.operator_metrics_exports import install_operator_metrics_module
from nimbusware_console.explainer_core.table_rows_csv import field_value_table_rows_csv
from nimbusware_console.explainer_core.workflow_exports import run_id_export_filename_slug
from nimbusware_orchestrator.preflight_histogram import build_histogram, empty_histogram
from nimbusware_projections.fields.preflight import PREFLIGHT_DISPLAY_FIELDS

_PREFLIGHT_FIELDS = PREFLIGHT_DISPLAY_FIELDS


def _stringify(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def preflight_history_from_timeline(
    timeline_body: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(timeline_body, Mapping):
        return None
    raw = timeline_body.get("preflight")
    return raw if isinstance(raw, dict) else None


def preflight_history_summary_rows(
    summary: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    if not summary:
        return []
    rows: list[dict[str, str]] = []
    for key, label in _PREFLIGHT_FIELDS:
        if key not in summary:
            continue
        rows.append({"field": label, "value": _stringify(summary.get(key))})
    return rows


preflight_history_summary_rows_csv = field_value_table_rows_csv


def preflight_history_export_json(summary: Mapping[str, Any] | None) -> str:
    return mapping_export_json(summary)


def preflight_history_export_filename_slug(run_id: str, *, max_len: int = 36) -> str:
    return run_id_export_filename_slug(run_id, max_len=max_len)


def preflight_history_histogram_mode_caption(
    summary: Mapping[str, Any] | None,
) -> str | None:
    if not summary:
        return None
    raw_samples = summary.get("health_latency_samples_ms")
    if isinstance(raw_samples, list) and raw_samples:
        samples = [int(s) for s in raw_samples if is_strict_int(s)]
        if samples:
            n = len(samples)
            sc = summary.get("preflight_latency_sample_count")
            tail = ""
            if is_strict_int(sc):
                tail = f" Persisted sample_count={sc}."
            return f"Histogram: **{n}** health latency sample(s) from timeline.{tail}"
    p95 = summary.get("p95_latency_ms")
    if is_strict_int(p95) and p95 >= 0:
        return (
            "Histogram: **legacy single-bar** fallback from p95_latency_ms only "
            "(no health_latency_samples_ms on this event)."
        )
    return None


def preflight_history_event_id_caption(
    summary: Mapping[str, Any] | None,
) -> str | None:
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
    if not isinstance(summary, Mapping):
        return None
    raw = summary.get("p95_latency_ms")
    if not isinstance(raw, int) or isinstance(raw, bool) or raw < 0:
        return None
    return f"Preflight p95 latency: **{raw}** ms."


def preflight_history_p95_source_caption(
    summary: Mapping[str, Any] | None,
) -> str | None:
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
    rows = preflight_history_latency_samples_table_rows(summary)
    if len(rows) < 2:
        return None
    return f"Preflight latency samples: **{len(rows)}** row(s) from timeline."


def preflight_history_histogram_payload(
    summary: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    if not summary:
        return None
    raw_samples = summary.get("health_latency_samples_ms")
    if isinstance(raw_samples, list) and raw_samples:
        samples = [int(s) for s in raw_samples if is_strict_int(s)]
        if samples:
            return build_histogram(samples)
    p95 = summary.get("p95_latency_ms")
    if is_strict_int(p95) and p95 >= 0:
        return build_histogram([p95])
    return empty_histogram()


def preflight_history_operator_metrics(
    summary: Mapping[str, Any] | None,
) -> dict[str, Any]:
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
    metrics["has_p95_latency"] = is_strict_int(p95) and p95 >= 0
    sc = summary.get("preflight_latency_sample_count")
    if is_strict_int(sc):
        metrics["sample_count"] = sc
        metrics["multisample"] = sc > 1
    raw_checks = summary.get("checks_passed")
    if isinstance(raw_checks, list):
        metrics["checks_passed_count"] = sum(
            1 for item in raw_checks if isinstance(item, str) and item.strip()
        )
    raw_samples = summary.get("health_latency_samples_ms")
    if isinstance(raw_samples, list):
        metrics["health_latency_samples_count"] = sum(1 for s in raw_samples if is_strict_int(s))
    vm = summary.get("validated_model_id")
    metrics["validated_model_present"] = vm is not None and str(vm).strip() != ""
    return metrics


def preflight_history_operator_metrics_table_rows(
    metrics: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    if not isinstance(metrics, Mapping):
        return []
    rows: list[dict[str, str]] = []
    if metrics.get("has_p95_latency") is True:
        rows.append({"field": "Has p95 latency", "value": "yes"})
    sc = metrics.get("sample_count", 0)
    if is_strict_int(sc) and sc > 0:
        rows.append({"field": "Sample count", "value": str(sc)})
    if metrics.get("multisample") is True:
        rows.append({"field": "Multisample", "value": "yes"})
    cpc = metrics.get("checks_passed_count", 0)
    if is_strict_int(cpc) and cpc > 0:
        rows.append({"field": "Checks passed count", "value": str(cpc)})
    hlc = metrics.get("health_latency_samples_count", 0)
    if is_strict_int(hlc) and hlc > 0:
        rows.append({"field": "Health latency samples", "value": str(hlc)})
    if metrics.get("validated_model_present") is True:
        rows.append({"field": "Validated model present", "value": "yes"})
    return rows


def preflight_history_operator_metrics_caption(
    metrics: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(metrics, Mapping):
        return None
    parts: list[str] = []
    if metrics.get("has_p95_latency") is True:
        parts.append("p95 present")
    sc = metrics.get("sample_count", 0)
    if is_strict_int(sc) and sc > 0:
        parts.append(f"**{sc}** sample(s)")
    if metrics.get("multisample") is True:
        parts.append("multisample")
    cpc = metrics.get("checks_passed_count", 0)
    if is_strict_int(cpc) and cpc > 0:
        parts.append(f"**{cpc}** check(s) passed")
    if metrics.get("validated_model_present") is True:
        parts.append("validated model")
    if not parts:
        return None
    return "Preflight history metrics: " + ", ".join(parts) + "."


(
    preflight_history_operator_metrics,
    preflight_history_operator_metrics_table_rows,
    preflight_history_operator_metrics_caption,
    preflight_history_operator_metrics_export_json,
    preflight_history_operator_metrics_table_rows_csv,
    _preflight_history_operator_metrics_exports_slug,
) = install_operator_metrics_module(
    globals(),
    module_prefix="preflight_history",
    metrics=preflight_history_operator_metrics,
    table_rows=preflight_history_operator_metrics_table_rows,
    caption=preflight_history_operator_metrics_caption,
    export_slug="preflight_history_operator_metrics",
)


def preflight_history_operator_metrics_export_filename_slug(
    run_id: str,
    *,
    max_len: int = 36,
) -> str:
    return preflight_history_export_filename_slug(run_id, max_len=max_len)

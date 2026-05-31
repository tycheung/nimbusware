from __future__ import annotations

import csv
import json
from collections.abc import Mapping, Sequence
from io import StringIO
from typing import Any


def preflight_pairs_from_history_response(
    body: Mapping[str, Any] | None,
) -> list[tuple[str, dict[str, Any] | None]]:
    if not isinstance(body, Mapping):
        return []
    raw_entries = body.get("entries")
    if not isinstance(raw_entries, list):
        return []
    pairs: list[tuple[str, dict[str, Any] | None]] = []
    for item in raw_entries:
        if not isinstance(item, Mapping):
            continue
        rid = item.get("run_id")
        if not isinstance(rid, str) or not rid.strip():
            continue
        pf = item.get("preflight")
        pairs.append((rid.strip(), pf if isinstance(pf, dict) else None))
    return pairs


def preflight_history_response_limit(body: Mapping[str, Any] | None) -> int | None:
    if not isinstance(body, Mapping):
        return None
    lim = body.get("limit")
    if isinstance(lim, int) and not isinstance(lim, bool):
        return lim
    return None


def preflight_history_response_runs_with_preflight(
    body: Mapping[str, Any] | None,
) -> int | None:
    if not isinstance(body, Mapping):
        return None
    raw = body.get("runs_with_preflight")
    if isinstance(raw, int) and not isinstance(raw, bool) and raw >= 0:
        return raw
    return None


def preflight_history_response_coverage_ratio(
    body: Mapping[str, Any] | None,
) -> float | None:
    if not isinstance(body, Mapping):
        return None
    raw = body.get("preflight_coverage_ratio")
    if isinstance(raw, (int, float)) and not isinstance(raw, bool):
        val = float(raw)
        if 0.0 <= val <= 1.0:
            return val
    return None


def preflight_history_response_runs_without_preflight(
    body: Mapping[str, Any] | None,
) -> int | None:
    if not isinstance(body, Mapping):
        return None
    raw = body.get("runs_without_preflight")
    if isinstance(raw, int) and not isinstance(raw, bool) and raw >= 0:
        return raw
    return None


def preflight_history_response_runs_with_multisample_preflight(
    body: Mapping[str, Any] | None,
) -> int | None:
    if not isinstance(body, Mapping):
        return None
    raw = body.get("runs_with_multisample_preflight")
    if isinstance(raw, int) and not isinstance(raw, bool) and raw >= 0:
        return raw
    return None


def preflight_history_response_p95_latency_coverage_ratio(
    body: Mapping[str, Any] | None,
) -> float | None:
    if not isinstance(body, Mapping):
        return None
    raw = body.get("p95_latency_coverage_ratio")
    if isinstance(raw, (int, float)) and not isinstance(raw, bool):
        val = float(raw)
        if 0.0 <= val <= 1.0:
            return val
    return None


def preflight_history_response_avg_p95_latency_ms(
    body: Mapping[str, Any] | None,
) -> float | None:
    if not isinstance(body, Mapping):
        return None
    raw = body.get("avg_p95_latency_ms")
    if isinstance(raw, (int, float)) and not isinstance(raw, bool):
        val = float(raw)
        if val >= 0:
            return val
    return None


def preflight_history_response_max_p95_latency_ms(
    body: Mapping[str, Any] | None,
) -> int | None:
    if not isinstance(body, Mapping):
        return None
    raw = body.get("max_p95_latency_ms")
    if isinstance(raw, int) and not isinstance(raw, bool) and raw >= 0:
        return raw
    return None


def preflight_history_response_runs_with_checks_passed(
    body: Mapping[str, Any] | None,
) -> int | None:
    if not isinstance(body, Mapping):
        return None
    raw = body.get("runs_with_checks_passed")
    if isinstance(raw, int) and not isinstance(raw, bool) and raw >= 0:
        return raw
    return None


def preflight_history_response_distinct_validated_model_id_count(
    body: Mapping[str, Any] | None,
) -> int | None:
    if not isinstance(body, Mapping):
        return None
    raw = body.get("distinct_validated_model_id_count")
    if isinstance(raw, int) and not isinstance(raw, bool) and raw >= 0:
        return raw
    return None


def preflight_history_response_metrics_export(
    body: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(body, Mapping):
        return None
    raw = body.get("metrics_export")
    return dict(raw) if isinstance(raw, Mapping) else None


def preflight_history_response_metrics_export_caption(
    body: Mapping[str, Any] | None,
) -> str | None:
    export = preflight_history_response_metrics_export(body)
    if not isinstance(export, Mapping):
        return None
    scanned = export.get("runs_scanned")
    total = export.get("window_total_matching_runs")
    has_more = export.get("has_more")
    schema_version = export.get("export_schema_version")
    window_consistent = export.get("export_window_consistent")
    filters = export.get("filters")
    status_filter: str | None = None
    if isinstance(filters, Mapping):
        raw_status = filters.get("status")
        if isinstance(raw_status, str) and raw_status.strip():
            status_filter = raw_status.strip()
    parts: list[str] = []
    if isinstance(scanned, int) and not isinstance(scanned, bool):
        parts.append(f"runs_scanned={scanned}")
    if isinstance(total, int) and not isinstance(total, bool):
        parts.append(f"window_total={total}")
    if isinstance(has_more, bool):
        parts.append(f"has_more={'yes' if has_more else 'no'}")
    if isinstance(schema_version, int) and not isinstance(schema_version, bool):
        parts.append(f"schema=v{schema_version}")
    if isinstance(window_consistent, bool):
        parts.append(f"window_consistent={'yes' if window_consistent else 'no'}")
    if status_filter is not None:
        parts.append(f"status={status_filter}")
    if parts:
        return "Preflight metrics export attached (" + ", ".join(parts) + ")."
    return "Preflight metrics export attached."


def preflight_history_metrics_export_download_json(
    body: Mapping[str, Any] | None,
) -> str:
    export = preflight_history_response_metrics_export(body)
    if not isinstance(export, Mapping):
        return "{}"
    return json.dumps(dict(export), indent=2, ensure_ascii=False)


def preflight_history_metrics_export_download_filename_slug() -> str:
    return "preflight_history_metrics_export"


def preflight_history_response_sli_caption(body: Mapping[str, Any] | None) -> str | None:
    with_pf = preflight_history_response_runs_with_preflight(body)
    without_pf = preflight_history_response_runs_without_preflight(body)
    coverage = preflight_history_response_coverage_ratio(body)
    if with_pf is None and without_pf is None and coverage is None:
        return None
    parts: list[str] = []
    if with_pf is not None:
        parts.append(f"with_preflight={with_pf}")
    if without_pf is not None:
        parts.append(f"without_preflight={without_pf}")
    if coverage is not None:
        parts.append(f"coverage={coverage:.3f}")
    avg_p95 = preflight_history_response_avg_p95_latency_ms(body)
    if avg_p95 is not None:
        parts.append(f"avg_p95_ms={avg_p95:.1f}")
    max_p95 = preflight_history_response_max_p95_latency_ms(body)
    if max_p95 is not None:
        parts.append(f"max_p95_ms={max_p95}")
    p95_cov = preflight_history_response_p95_latency_coverage_ratio(body)
    if p95_cov is not None:
        parts.append(f"p95_coverage={p95_cov:.3f}")
    multisample = preflight_history_response_runs_with_multisample_preflight(body)
    if multisample is not None:
        parts.append(f"multisample={multisample}")
    checks = preflight_history_response_runs_with_checks_passed(body)
    if checks is not None:
        parts.append(f"checks_passed_runs={checks}")
    distinct_models = preflight_history_response_distinct_validated_model_id_count(body)
    if distinct_models is not None:
        parts.append(f"distinct_validated_model_ids={distinct_models}")
    return "Preflight history SLI: " + ", ".join(parts) + "."



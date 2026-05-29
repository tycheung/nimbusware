"""Cross-run preflight trend helpers (PLAN_GAP §14 #1 / fo130).

Display helpers are pure (no Streamlit). :func:`fetch_preflight_history` is the
single HTTP entry point for fleet aggregation via ``GET /v1/preflight-history``.
Callers pass ``(run_id, preflight_summary | None)`` tuples in **API list order**
(typically ``newest_first`` so index ``1`` is the freshest run on the page).
"""

from __future__ import annotations

import csv
import json
from collections.abc import Mapping, Sequence
from io import StringIO
from typing import Any

import httpx


def preflight_pairs_from_history_response(
    body: Mapping[str, Any] | None,
) -> list[tuple[str, dict[str, Any] | None]]:
    """Map ``GET /v1/preflight-history`` JSON to cross-run trend row inputs."""
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
    """Return response ``limit`` when present (for operator captions)."""
    if not isinstance(body, Mapping):
        return None
    lim = body.get("limit")
    if isinstance(lim, int) and not isinstance(lim, bool):
        return lim
    return None


def preflight_history_response_runs_with_preflight(
    body: Mapping[str, Any] | None,
) -> int | None:
    """Return response ``runs_with_preflight`` when present."""
    if not isinstance(body, Mapping):
        return None
    raw = body.get("runs_with_preflight")
    if isinstance(raw, int) and not isinstance(raw, bool) and raw >= 0:
        return raw
    return None


def preflight_history_response_coverage_ratio(
    body: Mapping[str, Any] | None,
) -> float | None:
    """Return response ``preflight_coverage_ratio`` when present."""
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
    """Return response ``runs_without_preflight`` when present."""
    if not isinstance(body, Mapping):
        return None
    raw = body.get("runs_without_preflight")
    if isinstance(raw, int) and not isinstance(raw, bool) and raw >= 0:
        return raw
    return None


def preflight_history_response_runs_with_multisample_preflight(
    body: Mapping[str, Any] | None,
) -> int | None:
    """Return response ``runs_with_multisample_preflight`` when present."""
    if not isinstance(body, Mapping):
        return None
    raw = body.get("runs_with_multisample_preflight")
    if isinstance(raw, int) and not isinstance(raw, bool) and raw >= 0:
        return raw
    return None


def preflight_history_response_p95_latency_coverage_ratio(
    body: Mapping[str, Any] | None,
) -> float | None:
    """Return response ``p95_latency_coverage_ratio`` when present."""
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
    """Return response ``avg_p95_latency_ms`` when present."""
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
    """Return response ``max_p95_latency_ms`` when present."""
    if not isinstance(body, Mapping):
        return None
    raw = body.get("max_p95_latency_ms")
    if isinstance(raw, int) and not isinstance(raw, bool) and raw >= 0:
        return raw
    return None


def preflight_history_response_runs_with_checks_passed(
    body: Mapping[str, Any] | None,
) -> int | None:
    """Return response ``runs_with_checks_passed`` when present."""
    if not isinstance(body, Mapping):
        return None
    raw = body.get("runs_with_checks_passed")
    if isinstance(raw, int) and not isinstance(raw, bool) and raw >= 0:
        return raw
    return None


def preflight_history_response_distinct_validated_model_id_count(
    body: Mapping[str, Any] | None,
) -> int | None:
    """Return response ``distinct_validated_model_id_count`` when present."""
    if not isinstance(body, Mapping):
        return None
    raw = body.get("distinct_validated_model_id_count")
    if isinstance(raw, int) and not isinstance(raw, bool) and raw >= 0:
        return raw
    return None


def preflight_history_response_metrics_export(
    body: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    """Return optional ``metrics_export`` payload from ``GET /v1/preflight-history``."""
    if not isinstance(body, Mapping):
        return None
    raw = body.get("metrics_export")
    return dict(raw) if isinstance(raw, Mapping) else None


def preflight_history_response_metrics_export_caption(
    body: Mapping[str, Any] | None,
) -> str | None:
    """One-line caption for export diagnostics availability."""
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
    """Pretty JSON for the API ``metrics_export`` blob (empty object when absent)."""
    export = preflight_history_response_metrics_export(body)
    if not isinstance(export, Mapping):
        return "{}"
    return json.dumps(dict(export), indent=2, ensure_ascii=False)


def preflight_history_metrics_export_download_filename_slug() -> str:
    """Stable slug for fleet preflight metrics export download filenames."""
    return "preflight_history_metrics_export"


def preflight_history_response_sli_caption(body: Mapping[str, Any] | None) -> str | None:
    """One-line SLI caption from ``GET /v1/preflight-history`` aggregate fields."""
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


def fetch_preflight_history(
    api_base: str,
    *,
    limit: int,
    order: str = "newest_first",
    include_metrics_export: bool = False,
    headers: Mapping[str, str] | None = None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """``GET {api_base}/preflight-history`` (raises ``httpx.HTTPError`` on failure)."""
    base = str(api_base).rstrip("/")
    params: dict[str, str | int] = {
        "limit": max(1, min(50, int(limit))),
        "order": order,
    }
    if include_metrics_export:
        params["include_metrics_export"] = 1
    response = httpx.get(
        f"{base}/preflight-history",
        params=params,
        headers=dict(headers or {}),
        timeout=timeout,
    )
    response.raise_for_status()
    body = response.json()
    return body if isinstance(body, dict) else {}


def short_run_id_label(run_id: str, *, head: int = 8) -> str:
    """Stable short label for chart rows (not a security boundary)."""
    s = str(run_id).strip()
    if len(s) <= head:
        return s or "?"
    return f"{s[:head]}…"


def preflight_cross_run_trend_rows(
    pairs: list[tuple[str, dict[str, Any] | None]],
) -> list[dict[str, Any]]:
    """One row per input pair for tables / charts.

    ``p95_latency_ms`` is ``None`` when there is no usable projection (missing
    preflight or non-int / negative ``p95_latency_ms`` in the summary dict).
    """
    out: list[dict[str, Any]] = []
    for idx, (run_id, pf) in enumerate(pairs):
        label = short_run_id_label(run_id)
        base = {
            "run_index": idx + 1,
            "run_id": str(run_id),
            "run_label": label,
            "has_preflight": False,
            "p95_latency_ms": None,
            "sample_count": None,
            "validated_model_id": None,
            "checks_passed_count": None,
        }
        if pf is None:
            out.append(base)
            continue
        base["has_preflight"] = True
        p95 = pf.get("p95_latency_ms")
        if isinstance(p95, int) and not isinstance(p95, bool) and p95 >= 0:
            base["p95_latency_ms"] = p95
        sc = pf.get("preflight_latency_sample_count")
        if isinstance(sc, int) and not isinstance(sc, bool):
            base["sample_count"] = sc
        vm = pf.get("validated_model_id")
        if vm is not None:
            base["validated_model_id"] = str(vm)
        raw_checks = pf.get("checks_passed")
        if isinstance(raw_checks, list):
            n_checks = sum(
                1
                for item in raw_checks
                if isinstance(item, str) and item.strip()
            )
            if n_checks > 0:
                base["checks_passed_count"] = n_checks
        out.append(base)
    return out


_PREFLIGHT_CROSS_RUN_TREND_CSV_COLUMNS: tuple[str, ...] = (
    "run_index",
    "run_id",
    "run_label",
    "has_preflight",
    "p95_latency_ms",
    "sample_count",
    "validated_model_id",
    "checks_passed_count",
)


def _csv_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "True" if value else "False"
    return str(value)


def preflight_cross_run_trend_rows_csv(rows: Sequence[Mapping[str, Any]]) -> str:
    """Serialize cross-run preflight trend rows to CSV (UTF-8 text)."""
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_PREFLIGHT_CROSS_RUN_TREND_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow({k: _csv_cell(r.get(k)) for k in _PREFLIGHT_CROSS_RUN_TREND_CSV_COLUMNS})
    return buf.getvalue()


def preflight_cross_run_trend_export_json(rows: Sequence[Mapping[str, Any]]) -> str:
    """JSON export of cross-run preflight trend row dicts."""
    items = [dict(x) for x in rows if isinstance(x, Mapping)]
    return json.dumps(items, ensure_ascii=False, indent=2)


def preflight_cross_run_trend_export_filename_slug() -> str:
    """Stable slug for cross-run preflight trend download filenames."""
    return "preflight_trends"


def preflight_cross_run_trend_summary(rows: list[Mapping[str, Any]]) -> dict[str, Any]:
    """Counts for operator captions (bounded fan-out context)."""
    n = len(rows)
    with_pf = sum(1 for r in rows if r.get("has_preflight"))
    with_p95 = sum(1 for r in rows if isinstance(r.get("p95_latency_ms"), int))
    distinct_model_ids: set[str] = set()
    with_vm = 0
    for r in rows:
        if not isinstance(r, Mapping) or not r.get("has_preflight"):
            continue
        vm = r.get("validated_model_id")
        if isinstance(vm, str) and vm.strip():
            with_vm += 1
            distinct_model_ids.add(vm.strip())
    with_sc_int = 0
    with_sc_gt_one = 0
    for r in rows:
        if not isinstance(r, Mapping) or not r.get("has_preflight"):
            continue
        sc = r.get("sample_count")
        if isinstance(sc, int) and not isinstance(sc, bool):
            with_sc_int += 1
            if sc > 1:
                with_sc_gt_one += 1
    return {
        "runs": n,
        "with_preflight_projection": with_pf,
        "with_p95_latency": with_p95,
        "with_validated_model_id": with_vm,
        "distinct_validated_model_id_count": len(distinct_model_ids),
        "with_integer_sample_count": with_sc_int,
        "with_sample_count_gt_one": with_sc_gt_one,
    }


def preflight_cross_run_operator_metrics(
    summary: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Operator rollup from a precomputed cross-run trend summary dict."""
    if not isinstance(summary, Mapping):
        return {}
    return dict(summary)


def preflight_cross_run_operator_metrics_table_rows(
    metrics: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    """Two-column rows for ``st.dataframe`` (field / value)."""
    if not isinstance(metrics, Mapping) or not metrics:
        return []
    labels: tuple[tuple[str, str], ...] = (
        ("runs", "Runs scanned"),
        ("with_preflight_projection", "With preflight projection"),
        ("with_p95_latency", "With p95 latency"),
        ("with_validated_model_id", "With validated model id"),
        ("distinct_validated_model_id_count", "Distinct validated model ids"),
        ("with_integer_sample_count", "With integer sample count"),
        ("with_sample_count_gt_one", "With sample count > 1"),
    )
    rows: list[dict[str, str]] = []
    for key, label in labels:
        if key in metrics:
            rows.append({"field": label, "value": str(metrics.get(key))})
    return rows


def preflight_cross_run_operator_metrics_caption(
    metrics: Mapping[str, Any] | None,
) -> str | None:
    """One-line operator caption from cross-run trend summary counts."""
    if not isinstance(metrics, Mapping) or not metrics:
        return None
    runs = metrics.get("runs")
    with_pf = metrics.get("with_preflight_projection")
    with_p95 = metrics.get("with_p95_latency")
    if not isinstance(runs, int) or isinstance(runs, bool):
        return None
    parts = [f"**{runs}** run(s)"]
    if isinstance(with_pf, int) and not isinstance(with_pf, bool):
        parts.append(f"**{with_pf}** with preflight")
    if isinstance(with_p95, int) and not isinstance(with_p95, bool):
        parts.append(f"**{with_p95}** with p95")
    return "Cross-run preflight metrics: " + ", ".join(parts) + "."


_PREFLIGHT_CROSS_RUN_OPERATOR_METRICS_CSV_COLUMNS: tuple[str, ...] = (
    "field",
    "value",
)


def preflight_cross_run_operator_metrics_export_json(
    metrics: Mapping[str, Any] | None,
) -> str:
    """Pretty JSON for cross-run preflight operator metrics."""
    if not isinstance(metrics, Mapping):
        return "{}"
    return json.dumps(dict(metrics), indent=2, ensure_ascii=False)


def preflight_cross_run_operator_metrics_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    """Serialize cross-run preflight operator metrics rows to CSV."""
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_PREFLIGHT_CROSS_RUN_OPERATOR_METRICS_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow(
                {
                    k: r.get(k, "")
                    for k in _PREFLIGHT_CROSS_RUN_OPERATOR_METRICS_CSV_COLUMNS
                },
            )
    return buf.getvalue()


def preflight_cross_run_operator_metrics_export_filename_slug() -> str:
    """Stable slug for cross-run preflight operator metrics download filenames."""
    return f"{preflight_cross_run_trend_export_filename_slug()}_operator_metrics"


def _cross_run_row_usable_p95_ms(r: Mapping[str, Any]) -> bool:
    v = r.get("p95_latency_ms")
    return isinstance(v, int) and not isinstance(v, bool) and v >= 0


def preflight_cross_run_projection_without_p95_count(
    rows: list[Mapping[str, Any]],
) -> int:
    """Runs where timeline exposed ``preflight`` but ``p95_latency_ms`` was unusable."""
    n = 0
    for r in rows:
        if not isinstance(r, Mapping):
            continue
        if not r.get("has_preflight"):
            continue
        if _cross_run_row_usable_p95_ms(r):
            continue
        n += 1
    return n


def preflight_cross_run_p95_spread_ms(
    rows: list[Mapping[str, Any]],
) -> dict[str, int] | None:
    """Min / max / span over usable integer ``p95_latency_ms`` values (>=2 points)."""
    p95s: list[int] = []
    for r in rows:
        if not isinstance(r, Mapping):
            continue
        if not _cross_run_row_usable_p95_ms(r):
            continue
        v = r["p95_latency_ms"]
        p95s.append(int(v))
    if len(p95s) < 2:
        return None
    lo, hi = min(p95s), max(p95s)
    return {"min_p95_ms": lo, "max_p95_ms": hi, "span_ms": hi - lo, "n": len(p95s)}


def preflight_cross_run_p95_spread_caption(
    rows: list[Mapping[str, Any]],
) -> str | None:
    """Dedicated cross-run p95 min/max/span caption (>=2 usable p95 values)."""
    spread = preflight_cross_run_p95_spread_ms(rows)
    if not spread:
        return None
    return (
        f"Cross-run p95 spread: **{spread['min_p95_ms']}** / **{spread['max_p95_ms']}** ms "
        f"over **{spread['n']}** run(s) (span **{spread['span_ms']}** ms)."
    )


def preflight_cross_run_latency_sample_count_coverage_caption(
    rows: list[Mapping[str, Any]],
) -> str | None:
    """How many timeline preflight rows report an integer ``preflight_latency_sample_count``."""
    with_pf = 0
    with_sc = 0
    for r in rows:
        if not isinstance(r, Mapping):
            continue
        if not r.get("has_preflight"):
            continue
        with_pf += 1
        sc = r.get("sample_count")
        if isinstance(sc, int) and not isinstance(sc, bool):
            with_sc += 1
    if with_pf == 0:
        return None
    return (
        f"Latency ``preflight_latency_sample_count`` present for **{with_sc}** / **{with_pf}** "
        "run(s) with a preflight projection (others omit the field or use a non-integer value)."
    )


def preflight_cross_run_operator_depth_caption(
    rows: list[Mapping[str, Any]],
) -> str | None:
    """Second-line operator text: legacy projection without p95 + p95 spread."""
    parts: list[str] = []
    orphan = preflight_cross_run_projection_without_p95_count(rows)
    if orphan:
        parts.append(
            f"{orphan} run(s) have a preflight projection without a usable p95 "
            "(legacy or incomplete timeline payload).",
        )
    spread = preflight_cross_run_p95_spread_ms(rows)
    if spread:
        parts.append(
            f"p95 min / max over {spread['n']} runs with latency: "
            f"{spread['min_p95_ms']} / {spread['max_p95_ms']} ms "
            f"(span {spread['span_ms']} ms).",
        )
    if not parts:
        return None
    return " ".join(parts)


def preflight_cross_run_validated_model_id_coverage_caption(
    rows: list[Mapping[str, Any]],
) -> str | None:
    """How many distinct ``validated_model_id`` strings appear among preflight rows."""
    s = preflight_cross_run_trend_summary(rows)
    with_pf = int(s.get("with_preflight_projection") or 0)
    with_vm = int(s.get("with_validated_model_id") or 0)
    distinct = int(s.get("distinct_validated_model_id_count") or 0)
    if with_pf == 0 or with_vm == 0:
        return None
    return (
        f"``validated_model_id`` string present for **{with_vm}** / **{with_pf}** run(s) with "
        f"a preflight projection (**{distinct}** distinct id(s))."
    )


def preflight_cross_run_checks_passed_coverage_caption(
    rows: list[Mapping[str, Any]],
) -> str | None:
    """How many timeline preflight rows expose a non-empty ``checks_passed`` list."""
    with_pf = 0
    with_checks = 0
    for r in rows:
        if not isinstance(r, Mapping):
            continue
        if not r.get("has_preflight"):
            continue
        with_pf += 1
        cpc = r.get("checks_passed_count")
        if isinstance(cpc, int) and not isinstance(cpc, bool) and cpc > 0:
            with_checks += 1
    if with_pf == 0 or with_checks == 0:
        return None
    return (
        f"``checks_passed`` present for **{with_checks}** / **{with_pf}** "
        "run(s) with a preflight projection (others omit the field, use a non-list, "
        "or list only empty / non-string entries)."
    )


def preflight_cross_run_multisample_caption(
    rows: list[Mapping[str, Any]],
) -> str | None:
    """Surface how many runs report multisample preflight (integer ``sample_count`` > 1)."""
    s = preflight_cross_run_trend_summary(rows)
    pf = s.get("with_preflight_projection")
    if not isinstance(pf, int) or pf < 1:
        return None
    gt1 = s.get("with_sample_count_gt_one")
    if not isinstance(gt1, int) or isinstance(gt1, bool) or gt1 < 1:
        return None
    return (
        f"Multisample preflight (``preflight_latency_sample_count`` > **1**): **{gt1}** / **{pf}** "
        "run(s) with a projection."
    )

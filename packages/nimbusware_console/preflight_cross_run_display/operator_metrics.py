from __future__ import annotations

import csv
import json
from collections.abc import Mapping, Sequence
from io import StringIO
from typing import Any


from nimbusware_console.preflight_cross_run_display.trend import (
    preflight_cross_run_trend_export_filename_slug,
)
def preflight_cross_run_operator_metrics(
    summary: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if not isinstance(summary, Mapping):
        return {}
    return dict(summary)


def preflight_cross_run_operator_metrics_table_rows(
    metrics: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
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
    if not isinstance(metrics, Mapping):
        return "{}"
    return json.dumps(dict(metrics), indent=2, ensure_ascii=False)


def preflight_cross_run_operator_metrics_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
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
    return f"{preflight_cross_run_trend_export_filename_slug()}_operator_metrics"



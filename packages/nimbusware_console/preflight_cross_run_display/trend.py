from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from nimbusware_console.components.operator_metrics import (
    sequence_export_json,
    table_rows_csv,
)


def short_run_id_label(run_id: str, *, head: int = 8) -> str:
    s = str(run_id).strip()
    if len(s) <= head:
        return s or "?"
    return f"{s[:head]}…"


def preflight_cross_run_trend_rows(
    pairs: list[tuple[str, dict[str, Any] | None]],
) -> list[dict[str, Any]]:
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
            n_checks = sum(1 for item in raw_checks if isinstance(item, str) and item.strip())
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
    if not rows:
        return ""
    normalized = [
        {k: _csv_cell(r.get(k)) for k in _PREFLIGHT_CROSS_RUN_TREND_CSV_COLUMNS}
        for r in rows
        if isinstance(r, Mapping)
    ]
    return table_rows_csv(normalized, columns=_PREFLIGHT_CROSS_RUN_TREND_CSV_COLUMNS)


def preflight_cross_run_trend_export_json(rows: Sequence[Mapping[str, Any]]) -> str:
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        return "[]"
    return sequence_export_json([dict(x) for x in rows if isinstance(x, Mapping)])


def preflight_cross_run_trend_export_filename_slug() -> str:
    return "preflight_trends"


def preflight_cross_run_trend_summary(rows: list[Mapping[str, Any]]) -> dict[str, Any]:
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

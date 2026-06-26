from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from agent_core.coercion import is_strict_int
from nimbusware_console.preflight_cross_run_display.trend import (
    preflight_cross_run_trend_summary,
)


def _cross_run_row_usable_p95_ms(r: Mapping[str, Any]) -> bool:
    v = r.get("p95_latency_ms")
    return is_strict_int(v) and v >= 0


def preflight_cross_run_projection_without_p95_count(
    rows: list[Mapping[str, Any]],
) -> int:
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
    with_pf = 0
    with_sc = 0
    for r in rows:
        if not isinstance(r, Mapping):
            continue
        if not r.get("has_preflight"):
            continue
        with_pf += 1
        sc = r.get("sample_count")
        if is_strict_int(sc):
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
    with_pf = 0
    with_checks = 0
    for r in rows:
        if not isinstance(r, Mapping):
            continue
        if not r.get("has_preflight"):
            continue
        with_pf += 1
        cpc = r.get("checks_passed_count")
        if is_strict_int(cpc) and cpc > 0:
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

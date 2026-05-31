from __future__ import annotations

import csv
import json
import re
from collections.abc import Mapping, Sequence
from io import StringIO
from typing import Any

from nimbusware_console.universal_critique_timeline_display.rows import (
    universal_critique_timeline_export_filename_slug,
)


def universal_critique_timeline_operator_metrics(
    summary: Mapping[str, Any] | None,
) -> dict[str, Any]:
    metrics: dict[str, Any] = {
        "stage_count": 0,
        "fail_count": 0,
        "pass_count": 0,
        "fail_rate": None,
        "other_verdict_count": 0,
        "distinct_fail_stages": [],
        "default_enabled_effective": None,
        "unanimous_gate_effective": None,
        "failing_critics_total_count": 0,
    }
    if not isinstance(summary, Mapping):
        return metrics
    stages = summary.get("stages")
    fail_stage_names: set[str] = set()
    failing_critics_total = 0
    if isinstance(stages, list):
        for s in stages:
            if not isinstance(s, dict):
                continue
            fc = s.get("failing_critics")
            if isinstance(fc, list):
                failing_critics_total += len(fc)
            metrics["stage_count"] = int(metrics["stage_count"]) + 1
            verdict = s.get("verdict")
            if not isinstance(verdict, str):
                metrics["other_verdict_count"] = int(metrics["other_verdict_count"]) + 1
                continue
            key = verdict.strip().upper()
            if key == "FAIL":
                metrics["fail_count"] = int(metrics["fail_count"]) + 1
                sn = s.get("stage_name")
                if isinstance(sn, str) and sn.strip():
                    fail_stage_names.add(sn.strip())
            elif key == "PASS":
                metrics["pass_count"] = int(metrics["pass_count"]) + 1
            else:
                metrics["other_verdict_count"] = int(metrics["other_verdict_count"]) + 1
    if metrics["stage_count"] == 0:
        sc = summary.get("stage_count")
        if isinstance(sc, int) and not isinstance(sc, bool):
            metrics["stage_count"] = int(sc)
    if isinstance(summary.get("fail_count"), int) and not isinstance(
        summary.get("fail_count"),
        bool,
    ):
        metrics["fail_count"] = int(summary["fail_count"])
    if isinstance(summary.get("pass_count"), int) and not isinstance(
        summary.get("pass_count"),
        bool,
    ):
        metrics["pass_count"] = int(summary["pass_count"])
    fail_rate = summary.get("fail_rate")
    if isinstance(fail_rate, (int, float)) and not isinstance(fail_rate, bool):
        metrics["fail_rate"] = float(fail_rate)
    elif (
        isinstance(metrics.get("stage_count"), int)
        and metrics["stage_count"] > 0
        and isinstance(metrics.get("fail_count"), int)
    ):
        metrics["fail_rate"] = round(
            metrics["fail_count"] / metrics["stage_count"],
            4,
        )
    if not fail_stage_names:
        raw_distinct = summary.get("distinct_fail_stages")
        if isinstance(raw_distinct, list):
            for stage in raw_distinct:
                if isinstance(stage, str) and stage.strip():
                    fail_stage_names.add(stage.strip())
    metrics["distinct_fail_stages"] = sorted(fail_stage_names)
    metrics["failing_critics_total_count"] = failing_critics_total
    for key in ("default_enabled_effective", "unanimous_gate_effective"):
        val = summary.get(key)
        if isinstance(val, bool):
            metrics[key] = val
    cc = summary.get("critique_coverage")
    if isinstance(cc, Mapping):
        for src_key, out_key in (
            ("registry_producers", "registry_producer_count"),
            ("paired_producers", "paired_producer_count"),
            ("unpaired_producers", "unpaired_producer_count"),
        ):
            raw = cc.get(src_key)
            if isinstance(raw, list):
                metrics[out_key] = len(raw)
    return metrics


def universal_critique_timeline_operator_metrics_table_rows(
    metrics: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    if not isinstance(metrics, Mapping):
        return []
    rows: list[dict[str, str]] = [
        {"field": "Stage count", "value": str(metrics.get("stage_count", 0))},
        {"field": "FAIL", "value": str(metrics.get("fail_count", 0))},
        {"field": "PASS", "value": str(metrics.get("pass_count", 0))},
    ]
    fail_rate = metrics.get("fail_rate")
    if isinstance(fail_rate, (int, float)) and not isinstance(fail_rate, bool):
        rows.append({"field": "FAIL rate", "value": f"{100.0 * float(fail_rate):.1f}%"})
    other = metrics.get("other_verdict_count", 0)
    if isinstance(other, int) and not isinstance(other, bool) and other > 0:
        rows.append({"field": "Other verdict", "value": str(other)})
    fail_stages = metrics.get("distinct_fail_stages")
    if isinstance(fail_stages, list) and fail_stages:
        rows.append(
            {
                "field": "Distinct FAIL stages",
                "value": ", ".join(str(x) for x in fail_stages if isinstance(x, str)),
            },
        )
    for label, key in (
        ("Default-on effective", "default_enabled_effective"),
        ("Unanimous gate effective", "unanimous_gate_effective"),
    ):
        val = metrics.get(key)
        if isinstance(val, bool):
            rows.append({"field": label, "value": str(val)})
    for label, key in (
        ("Registry producers", "registry_producer_count"),
        ("Paired producers", "paired_producer_count"),
        ("Unpaired producers", "unpaired_producer_count"),
    ):
        n = metrics.get(key)
        if isinstance(n, int) and not isinstance(n, bool):
            rows.append({"field": label, "value": str(n)})
    fc_total = metrics.get("failing_critics_total_count")
    if isinstance(fc_total, int) and not isinstance(fc_total, bool) and fc_total > 0:
        rows.append({"field": "Failing critics (total)", "value": str(fc_total)})
    return rows


def universal_critique_timeline_operator_metrics_caption(
    metrics: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(metrics, Mapping):
        return None
    stage_count = metrics.get("stage_count")
    fail_count = metrics.get("fail_count")
    if isinstance(stage_count, bool) or not isinstance(stage_count, int):
        return None
    if isinstance(fail_count, bool) or not isinstance(fail_count, int):
        return None
    if stage_count < 1:
        return None
    pass_count = metrics.get("pass_count")
    other = metrics.get("other_verdict_count", 0)
    other_suffix = ""
    if isinstance(other, int) and not isinstance(other, bool) and other > 0:
        other_suffix = f", **{other}** other verdict(s)"
    policy_suffix = ""
    default_on = metrics.get("default_enabled_effective")
    if default_on is True:
        policy_suffix = "; default-on **enabled**"
    elif default_on is False:
        policy_suffix = "; default-on **off**"
    unanimous = metrics.get("unanimous_gate_effective")
    if unanimous is True:
        policy_suffix += "; unanimous gate **on**"
    elif unanimous is False:
        policy_suffix += "; unanimous gate legacy"
    reg_n = metrics.get("registry_producer_count")
    if isinstance(reg_n, int) and not isinstance(reg_n, bool) and reg_n > 0:
        policy_suffix += f"; **{reg_n}** registry producer(s)"
    fc_total = metrics.get("failing_critics_total_count")
    if isinstance(fc_total, int) and not isinstance(fc_total, bool) and fc_total > 0:
        policy_suffix += f"; **{fc_total}** failing critic(s)"
    if isinstance(pass_count, int) and not isinstance(pass_count, bool) and pass_count > 0:
        return (
            f"Universal critique gates: **{fail_count}** FAIL, **{pass_count}** PASS"
            f"{other_suffix} of **{stage_count}** stage(s) on this timeline"
            f"{policy_suffix}."
        )
    return (
        f"Universal critique gates: **{fail_count}** FAIL{other_suffix} of "
        f"**{stage_count}** stage(s) on this timeline{policy_suffix}."
    )


def universal_critique_timeline_fail_rate_caption(
    summary: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(summary, Mapping):
        return None
    fail_count = summary.get("fail_count")
    stage_count = summary.get("stage_count")
    if (
        not isinstance(fail_count, int)
        or isinstance(fail_count, bool)
        or not isinstance(stage_count, int)
        or isinstance(stage_count, bool)
        or stage_count < 1
    ):
        return None
    pct = (100.0 * fail_count) / stage_count
    return f"Universal critique FAIL rate: **{pct:.1f}%** ({fail_count}/{stage_count})."


def universal_critique_timeline_default_on_caption(
    summary: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(summary, Mapping):
        return None
    val = summary.get("default_enabled_effective")
    if val is True:
        return (
            "Universal critique default-on: **enabled** on this run "
            "(workflow ``default_enabled`` frozen at create)."
        )
    if val is False:
        return (
            "Universal critique default-on: **off** on this run "
            "(panels need explicit ``enabled`` or env gates)."
        )
    return None


def universal_critique_unanimous_gate_caption(summary: Mapping[str, Any] | None) -> str | None:
    if not isinstance(summary, Mapping):
        return None
    val = summary.get("unanimous_gate_effective")
    if val is True:
        return "Unanimous gate enforcement: enabled."
    if val is False:
        return "Unanimous gate enforcement: legacy behavior."
    return None


_UNIVERSAL_CRITIQUE_OPERATOR_METRICS_CSV_COLUMNS: tuple[str, ...] = ("field", "value")


def universal_critique_timeline_operator_metrics_export_json(
    metrics: Mapping[str, Any] | None,
) -> str:
    if not isinstance(metrics, Mapping):
        return "{}"
    return json.dumps(dict(metrics), indent=2, ensure_ascii=False)


def universal_critique_timeline_operator_metrics_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_UNIVERSAL_CRITIQUE_OPERATOR_METRICS_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow(
                {
                    k: r.get(k, "")
                    for k in _UNIVERSAL_CRITIQUE_OPERATOR_METRICS_CSV_COLUMNS
                },
            )
    return buf.getvalue()


def universal_critique_timeline_operator_metrics_export_filename_slug(
    run_id: str,
    *,
    max_len: int = 36,
) -> str:
    return universal_critique_timeline_export_filename_slug(run_id, max_len=max_len)

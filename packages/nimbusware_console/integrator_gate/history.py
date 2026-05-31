from __future__ import annotations

from nimbusware_console.components.operator_metrics import (
    field_value_table_rows_csv,
    mapping_export_json,
    table_rows_csv,
)
import csv
import json
import re
from collections.abc import Mapping, Sequence
from io import StringIO
from typing import Any

from nimbusware_console.integrator_gate._helpers import (
    _format_tag_list_sample,
    _optional_float,
    _stringify,
)
def integrator_gate_history_table_rows(history: list[dict[str, Any]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for i, g in enumerate(history, start=1):
        rows.append(
            {
                "#": str(i),
                "Occurred at": _stringify(g.get("occurred_at")),
                "Verdict": _stringify(g.get("verdict")),
                "Failure reason": _stringify(g.get("failure_reason_code")),
                "Score": _stringify(g.get("integrator_score")),
                "Min pass": _stringify(g.get("min_score_to_pass")),
                "Bundle": _stringify(g.get("bundle_id")),
                "Bundle title": _stringify(g.get("bundle_title")),
                "Matched tags": _format_tag_list_sample(g.get("integrator_matched_tags")),
                "Stage": _stringify(g.get("stage_name")),
                "Event id": _stringify(g.get("event_id")),
            },
        )
    return rows


_INTEGRATOR_GATE_HISTORY_CSV_COLUMNS: tuple[str, ...] = (
    "#",
    "Occurred at",
    "Verdict",
    "Failure reason",
    "Score",
    "Min pass",
    "Bundle",
    "Bundle title",
    "Matched tags",
    "Stage",
    "Event id",
)


def integrator_gate_history_table_rows_csv(rows: Sequence[Mapping[str, str]]) -> str:
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_INTEGRATOR_GATE_HISTORY_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow({k: r.get(k, "") for k in _INTEGRATOR_GATE_HISTORY_CSV_COLUMNS})
    return buf.getvalue()


def integrator_gate_history_export_json(history: Sequence[Mapping[str, Any]]) -> str:
    items = [dict(x) for x in history if isinstance(x, Mapping)]
    return json.dumps(items, ensure_ascii=False, indent=2)


def integrator_gate_history_export_filename_slug(run_id: str, *, max_len: int = 36) -> str:
    raw = str(run_id).strip().lower()
    slug = re.sub(r"[^a-z0-9_.-]+", "_", raw).strip("._-") or "run"
    return slug[:max_len]


def integrator_gate_history_operator_metrics(
    history: list[dict[str, Any]],
) -> dict[str, Any]:
    if not history:
        return {"gate_event_count": 0}
    verdict_counts: dict[str, int] = {}
    scores: list[float] = []
    bundle_ids: set[str] = set()
    for g in history:
        v = g.get("verdict")
        if v is None:
            vk = "UNKNOWN"
        else:
            vs = str(v).strip()
            vk = vs.upper() if vs else "UNKNOWN"
        verdict_counts[vk] = verdict_counts.get(vk, 0) + 1
        sf = _optional_float(g.get("integrator_score"))
        if sf is not None:
            scores.append(sf)
        bid = g.get("bundle_id")
        if bid is not None:
            s = str(bid).strip()
            if s:
                bundle_ids.add(s)
    latest = history[-1]
    score_latest = _optional_float(latest.get("integrator_score"))
    min_latest = _optional_float(latest.get("min_score_to_pass"))
    margin: float | None = None
    if score_latest is not None and min_latest is not None:
        margin = round(score_latest - min_latest, 6)
    out: dict[str, Any] = {
        "gate_event_count": len(history),
        "verdict_counts": dict(sorted(verdict_counts.items())),
        "distinct_bundle_ids": sorted(bundle_ids),
        "distinct_bundle_id_count": len(bundle_ids),
    }
    if scores:
        out["integrator_score_min"] = round(min(scores), 6)
        out["integrator_score_max"] = round(max(scores), 6)
    if margin is not None:
        out["latest_score_minus_min_pass"] = margin
    return out


def integrator_gate_history_entry_count_caption(
    history: list[dict[str, Any]] | None,
) -> str | None:
    if not history:
        return None
    n = len(history)
    word = "decision" if n == 1 else "decisions"
    return f"Integrator gate history: **{n}** {word} in this timeline view."


def integrator_gate_history_failure_reason_caption(
    history: list[dict[str, Any]] | None,
) -> str | None:
    if not history:
        return None
    for g in reversed(history):
        if not isinstance(g, dict):
            continue
        frc = g.get("failure_reason_code")
        if not isinstance(frc, str) or not frc.strip():
            continue
        verdict = _stringify(g.get("verdict"))
        return f"Latest gate failure reason: {frc.strip()} (verdict {verdict})."
    return None


def integrator_gate_history_distinct_bundles_caption(
    metrics: Mapping[str, Any] | None,
) -> str | None:
    if not metrics:
        return None
    n_events = int(metrics.get("gate_event_count", 0) or 0)
    if n_events < 1:
        return None
    dcnt = metrics.get("distinct_bundle_id_count")
    if not isinstance(dcnt, int) or isinstance(dcnt, bool) or dcnt < 0:
        return None
    suffix = "id" if dcnt == 1 else "ids"
    return (
        f"Integrator gate history: **{dcnt}** distinct bundle {suffix} in this view."
    )


def integrator_gate_history_score_range_caption(
    metrics: Mapping[str, Any] | None,
) -> str | None:
    if not metrics:
        return None
    n_events = int(metrics.get("gate_event_count", 0) or 0)
    if n_events < 1:
        return None
    smin = _optional_float(metrics.get("integrator_score_min"))
    smax = _optional_float(metrics.get("integrator_score_max"))
    if smin is None or smax is None:
        return None
    return (
        f"Integrator gate history score range: **{smin}** .. **{smax}** "
        "(numeric rows only)."
    )


def integrator_gate_history_latest_margin_caption(
    metrics: Mapping[str, Any] | None,
) -> str | None:
    if not metrics:
        return None
    n_events = int(metrics.get("gate_event_count", 0) or 0)
    if n_events < 1:
        return None
    margin = _optional_float(metrics.get("latest_score_minus_min_pass"))
    if margin is None:
        return None
    return (
        f"Integrator gate history latest margin: **{margin}** "
        "(score − min_pass on latest row)."
    )


def integrator_gate_history_verdict_tally_caption(
    metrics: Mapping[str, Any] | None,
) -> str | None:
    if not metrics:
        return None
    vc = metrics.get("verdict_counts")
    if not isinstance(vc, dict) or not vc:
        return None
    parts = [f"{k}={v}" for k, v in sorted(vc.items())]
    if not parts:
        return None
    return "Integrator gate history verdicts: " + ", ".join(parts) + "."


def integrator_gate_history_operator_metrics_caption(
    metrics: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(metrics, Mapping):
        return None
    n_events = int(metrics.get("gate_event_count", 0) or 0)
    if n_events < 1:
        return None
    word = "event" if n_events == 1 else "events"
    parts: list[str] = [f"**{n_events}** gate {word} in view"]
    vc = metrics.get("verdict_counts")
    if isinstance(vc, dict) and vc:
        tally = ", ".join(f"{k}={v}" for k, v in sorted(vc.items()))
        parts.append(f"verdicts {tally}")
    dcnt = metrics.get("distinct_bundle_id_count")
    if isinstance(dcnt, int) and not isinstance(dcnt, bool) and dcnt > 0:
        suffix = "id" if dcnt == 1 else "ids"
        parts.append(f"**{dcnt}** bundle {suffix}")
    margin = _optional_float(metrics.get("latest_score_minus_min_pass"))
    if margin is not None:
        parts.append(f"latest margin **{margin:+.6g}**")
    return "Integrator gate history operator metrics: " + ", ".join(parts) + "."


def integrator_gate_history_metrics_table_rows(
    metrics: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    if not metrics:
        return []
    rows: list[dict[str, str]] = []
    n = int(metrics.get("gate_event_count", 0) or 0)
    rows.append({"field": "Gate events in view", "value": str(n)})
    if n == 0:
        return rows
    vc = metrics.get("verdict_counts")
    if isinstance(vc, dict) and vc:
        parts = [f"{k}: {v}" for k, v in sorted(vc.items())]
        rows.append({"field": "Verdict tally", "value": "; ".join(parts)})
    dcnt = metrics.get("distinct_bundle_id_count")
    if dcnt is not None:
        rows.append({"field": "Distinct bundle ids", "value": str(dcnt)})
    db = metrics.get("distinct_bundle_ids")
    if isinstance(db, list) and db:
        rows.append(
            {
                "field": "Bundle id list",
                "value": ", ".join(str(x) for x in db),
            },
        )
    smin = metrics.get("integrator_score_min")
    smax = metrics.get("integrator_score_max")
    if smin is not None and smax is not None:
        rows.append(
            {
                "field": "Integrator score range (numeric rows)",
                "value": f"{smin} .. {smax}",
            },
        )
    margin = metrics.get("latest_score_minus_min_pass")
    if margin is not None:
        rows.append(
            {
                "field": "Latest score minus min pass",
                "value": str(margin),
            },
        )
    return rows



def integrator_gate_history_operator_metrics_export_json(
    metrics: Mapping[str, Any] | None,
) -> str:
    return mapping_export_json(metrics)


def integrator_gate_history_operator_metrics_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    return field_value_table_rows_csv(rows)


def integrator_gate_history_operator_metrics_export_filename_slug(
    run_id: str,
    *,
    max_len: int = 36,
) -> str:
    return integrator_gate_history_export_filename_slug(run_id, max_len=max_len)




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
    _optional_float,
    _stringify,
    integrator_gate_from_timeline,
    integrator_gate_history_from_timeline,
)
from nimbusware_console.integrator_gate.history import (
    integrator_gate_history_operator_metrics,
)
def integrator_gate_latest_operator_metrics_export_json(
    metrics: Mapping[str, Any] | None,
) -> str:
    if not isinstance(metrics, Mapping) or not metrics.get("present"):
        return "{}"
    return json.dumps(dict(metrics), indent=2, ensure_ascii=False)


def integrator_gate_latest_operator_metrics_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    return field_value_table_rows_csv(rows)


def integrator_gate_latest_operator_metrics_export_filename_slug(
    run_id: str,
    *,
    max_len: int = 36,
) -> str:
    return integrator_gate_latest_export_filename_slug(run_id, max_len=max_len)



def integrator_gate_delta_operator_metrics_export_json(
    metrics: Mapping[str, Any] | None,
) -> str:
    if not isinstance(metrics, Mapping) or not metrics.get("present"):
        return "{}"
    return json.dumps(dict(metrics), indent=2, ensure_ascii=False)


def integrator_gate_delta_operator_metrics_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    return field_value_table_rows_csv(rows)


def integrator_gate_delta_operator_metrics_export_filename_slug(
    run_id: str,
    *,
    max_len: int = 36,
) -> str:
    return integrator_gate_delta_export_filename_slug(run_id, max_len=max_len)


def integrator_gate_delta_from_timeline(
    timeline_body: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(timeline_body, Mapping):
        return None
    raw = timeline_body.get("integrator_gate_delta")
    return raw if isinstance(raw, dict) else None


_DELTA_FIELDS: tuple[tuple[str, str], ...] = (
    ("integrator_score_delta", "Score delta (current − prior)"),
    ("verdict_changed", "Verdict changed"),
    ("bundle_id_changed", "Bundle id changed"),
    ("previous_verdict", "Previous verdict"),
    ("current_verdict", "Current verdict"),
    ("min_score_to_pass", "Min score to pass (current gate)"),
    ("previous_event_id", "Previous event id"),
    ("current_event_id", "Current event id"),
)


def integrator_gate_delta_summary_rows(delta: Mapping[str, Any] | None) -> list[dict[str, str]]:
    if not delta:
        return []
    rows: list[dict[str, str]] = []
    for key, label in _DELTA_FIELDS:
        if key not in delta:
            continue
        rows.append({"field": label, "value": _stringify(delta.get(key))})
    return rows



def integrator_gate_delta_summary_rows_csv(rows: Sequence[Mapping[str, str]]) -> str:
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_INTEGRATOR_GATE_DELTA_SUMMARY_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow(
                {k: r.get(k, "") for k in _INTEGRATOR_GATE_DELTA_SUMMARY_CSV_COLUMNS},
            )
    return buf.getvalue()


def integrator_gate_delta_export_json(delta: Mapping[str, Any] | None) -> str:
    if not isinstance(delta, Mapping):
        return "{}"
    return json.dumps(dict(delta), ensure_ascii=False, indent=2)


def integrator_gate_delta_export_filename_slug(run_id: str, *, max_len: int = 36) -> str:
    raw = str(run_id).strip().lower()
    slug = re.sub(r"[^a-z0-9_.-]+", "_", raw).strip("._-") or "run"
    return slug[:max_len]


def integrator_gate_summary_rows(ig: Mapping[str, Any] | None) -> list[dict[str, str]]:
    if not ig:
        return []
    rows: list[dict[str, str]] = []
    for key, label in _INTEGRATOR_GATE_FIELDS:
        if key not in ig:
            continue
        rows.append({"field": label, "value": _stringify(ig.get(key))})
    return rows



def integrator_gate_latest_summary_rows_csv(rows: Sequence[Mapping[str, str]]) -> str:
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_INTEGRATOR_GATE_LATEST_SUMMARY_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow(
                {k: r.get(k, "") for k in _INTEGRATOR_GATE_LATEST_SUMMARY_CSV_COLUMNS},
            )
    return buf.getvalue()


def integrator_gate_latest_export_json(ig: Mapping[str, Any] | None) -> str:
    if not isinstance(ig, Mapping):
        return "{}"
    return json.dumps(dict(ig), ensure_ascii=False, indent=2)


def integrator_gate_latest_export_filename_slug(run_id: str, *, max_len: int = 36) -> str:
    raw = str(run_id).strip().lower()
    slug = re.sub(r"[^a-z0-9_.-]+", "_", raw).strip("._-") or "run"
    return slug[:max_len]


def _string_tag_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for x in value:
        if isinstance(x, str) and x.strip():
            out.append(x.strip())
    return out


def integrator_gate_latest_operator_metrics(
    ig: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if not ig:
        return {"present": False}
    project = set(_string_tag_list(ig.get("integrator_project_tags")))
    matched = set(_string_tag_list(ig.get("integrator_matched_tags")))
    overlap = sorted(project & matched)
    score = _optional_float(ig.get("integrator_score"))
    min_pass = _optional_float(ig.get("min_score_to_pass"))
    margin: float | None = None
    passes_numeric: bool | None = None
    if score is not None and min_pass is not None:
        margin = round(score - min_pass, 6)
        passes_numeric = score >= min_pass
    frc = ig.get("failure_reason_code")
    ranking = ig.get("bundle_compatibility_ranking")
    ranking_count = ig.get("bundle_compatibility_ranking_count")
    if isinstance(ranking_count, int) and not isinstance(ranking_count, bool):
        n_ranked = ranking_count
    elif isinstance(ranking, list):
        n_ranked = len(ranking)
    else:
        n_ranked = None
    sel_rank = ig.get("selected_bundle_rank")
    out: dict[str, Any] = {
        "present": True,
        "integrator_project_tags_count": len(project),
        "integrator_bundle_tags_count": len(_string_tag_list(ig.get("integrator_bundle_tags"))),
        "integrator_matched_tags_count": len(matched),
        "tag_overlap_count": len(overlap),
        "tag_overlap": overlap,
    }
    if isinstance(n_ranked, int) and n_ranked >= 0:
        out["bundle_compatibility_ranking_count"] = n_ranked
    if isinstance(sel_rank, int) and not isinstance(sel_rank, bool):
        out["selected_bundle_rank"] = sel_rank
    if score is not None:
        out["integrator_score"] = score
    if min_pass is not None:
        out["min_score_to_pass"] = min_pass
    if frc is not None and str(frc).strip():
        out["failure_reason_code"] = str(frc).strip()
    if margin is not None:
        out["latest_score_minus_min_pass"] = margin
    if passes_numeric is not None:
        out["score_meets_min_numeric"] = passes_numeric
    return out


def integrator_gate_compatibility_ranking_table_rows(
    ig: Mapping[str, Any] | None,
    *,
    max_rows: int = 10,
) -> list[dict[str, str]]:
    if not isinstance(ig, Mapping):
        return []
    raw = ig.get("bundle_compatibility_ranking")
    if not isinstance(raw, list):
        return []
    cap = max(1, int(max_rows))
    rows: list[dict[str, str]] = []
    for i, item in enumerate(raw[:cap], start=1):
        if not isinstance(item, dict):
            continue
        bid = item.get("bundle_id")
        score = item.get("score")
        passes = item.get("passes_gate")
        title = item.get("title")
        rows.append(
            {
                "rank": str(i - 1),
                "bundle_id": _stringify(bid),
                "title": _stringify(title) if title is not None else "—",
                "score": _stringify(score),
                "passes_gate": _stringify(passes),
            }
        )
    return rows


def integrator_gate_compatibility_ranking_caption(
    ig: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(ig, Mapping):
        return None
    ranking = ig.get("bundle_compatibility_ranking")
    if not isinstance(ranking, list) or not ranking:
        return None
    count = ig.get("bundle_compatibility_ranking_count")
    n = int(count) if isinstance(count, int) and not isinstance(count, bool) else len(ranking)
    sel_rank = ig.get("selected_bundle_rank")
    sel_id = ig.get("selected_bundle_id") or ig.get("bundle_id")
    parts = [f"**{n}** catalog candidate(s) ranked by integrator score"]
    if isinstance(sel_rank, int) and not isinstance(sel_rank, bool):
        parts.append(f"selected bundle `{sel_id}` at rank **{sel_rank}**")
    elif isinstance(sel_id, str) and sel_id.strip():
        parts.append(f"selected bundle `{sel_id.strip()}`")
    top = ranking[0] if isinstance(ranking[0], dict) else None
    if top and top.get("bundle_id"):
        score = top.get("score")
        if isinstance(score, (int, float)) and not isinstance(score, bool):
            parts.append(f"top score **{score:.4g}** (`{top.get('bundle_id')}`)")
    return "Integrator compatibility ranking: " + "; ".join(parts) + "."


def integrator_gate_latest_bundle_id_caption(
    ig: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(ig, Mapping):
        return None
    raw = ig.get("bundle_id")
    if not isinstance(raw, str):
        return None
    text = raw.strip()
    if not text:
        return None
    return f"Integrator gate bundle_id: `{text}`."


def integrator_gate_latest_score_margin_caption(
    ig: Mapping[str, Any] | None,
) -> str | None:
    metrics = integrator_gate_latest_operator_metrics(ig)
    if not metrics.get("present"):
        return None
    parts: list[str] = []
    margin = metrics.get("latest_score_minus_min_pass")
    if isinstance(margin, (int, float)) and not isinstance(margin, bool):
        meets = metrics.get("score_meets_min_numeric")
        if meets is True:
            parts.append(f"score minus min pass: **{margin:+.6g}** (meets numeric bar)")
        elif meets is False:
            parts.append(f"score minus min pass: **{margin:+.6g}** (below numeric bar)")
        else:
            parts.append(f"score minus min pass: **{margin:+.6g}**")
    frc = metrics.get("failure_reason_code")
    if isinstance(frc, str) and frc.strip():
        parts.append(f"failure_reason_code={frc.strip()}")
    if not parts:
        return None
    return "Latest integrator gate: " + "; ".join(parts) + "."


def integrator_gate_latest_tag_overlap_caption(
    ig: Mapping[str, Any] | None,
) -> str | None:
    metrics = integrator_gate_latest_operator_metrics(ig)
    if not metrics.get("present"):
        return None
    overlap = metrics.get("tag_overlap_count")
    project_n = metrics.get("integrator_project_tags_count")
    matched_n = metrics.get("integrator_matched_tags_count")
    if not all(
        isinstance(x, int) and not isinstance(x, bool)
        for x in (overlap, project_n, matched_n)
    ):
        return None
    if project_n == 0 and matched_n == 0 and overlap == 0:
        return None
    return (
        f"Latest integrator gate tags: **{overlap}** matched of "
        f"**{project_n}** project tag(s)."
    )


def integrator_gate_latest_operator_metrics_caption(
    metrics: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(metrics, Mapping) or metrics.get("present") is not True:
        return None
    parts: list[str] = []
    score = metrics.get("integrator_score")
    if isinstance(score, (int, float)) and not isinstance(score, bool):
        parts.append(f"integrator score **{float(score):.4g}**")
    min_pass = metrics.get("min_score_to_pass")
    if isinstance(min_pass, (int, float)) and not isinstance(min_pass, bool):
        parts.append(f"min pass **{float(min_pass):.4g}**")
    overlap = metrics.get("tag_overlap_count")
    project_n = metrics.get("integrator_project_tags_count")
    if (
        isinstance(overlap, int)
        and not isinstance(overlap, bool)
        and isinstance(project_n, int)
        and not isinstance(project_n, bool)
        and (project_n > 0 or overlap > 0)
    ):
        parts.append(f"**{overlap}** tag overlap of **{project_n}** project tag(s)")
    margin = metrics.get("latest_score_minus_min_pass")
    if isinstance(margin, (int, float)) and not isinstance(margin, bool):
        meets = metrics.get("score_meets_min_numeric")
        if meets is True:
            parts.append(f"score minus min pass **{margin:+.6g}** (meets bar)")
        elif meets is False:
            parts.append(f"score minus min pass **{margin:+.6g}** (below bar)")
        else:
            parts.append(f"score minus min pass **{margin:+.6g}**")
    frc = metrics.get("failure_reason_code")
    if isinstance(frc, str) and frc.strip():
        parts.append(f"failure_reason_code={frc.strip()}")
    n_ranked = metrics.get("bundle_compatibility_ranking_count")
    if isinstance(n_ranked, int) and not isinstance(n_ranked, bool) and n_ranked > 0:
        parts.append(f"**{n_ranked}** ranked candidate(s)")
    sel_rank = metrics.get("selected_bundle_rank")
    if isinstance(sel_rank, int) and not isinstance(sel_rank, bool):
        parts.append(f"selected rank **{sel_rank}**")
    if not parts:
        return None
    return "Latest integrator gate operator metrics: " + ", ".join(parts) + "."


def integrator_gate_latest_metrics_table_rows(
    metrics: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    if not metrics or not metrics.get("present"):
        return []
    rows: list[dict[str, str]] = []
    rows.append(
        {
            "field": "Project tags (count)",
            "value": str(metrics.get("integrator_project_tags_count", 0)),
        },
    )
    rows.append(
        {
            "field": "Matched tags (count)",
            "value": str(metrics.get("integrator_matched_tags_count", 0)),
        },
    )
    rows.append(
        {
            "field": "Tag overlap (intersection)",
            "value": str(metrics.get("tag_overlap_count", 0)),
        },
    )
    ov = metrics.get("tag_overlap")
    if isinstance(ov, list) and ov:
        rows.append({"field": "Overlap tag list", "value": ", ".join(str(t) for t in ov)})
    rows.append(
        {
            "field": "Bundle tags (count)",
            "value": str(metrics.get("integrator_bundle_tags_count", 0)),
        },
    )
    if "integrator_score" in metrics:
        rows.append(
            {
                "field": "Integrator score",
                "value": f"{float(metrics['integrator_score']):.6g}",
            },
        )
    if "min_score_to_pass" in metrics:
        rows.append(
            {
                "field": "Min score to pass",
                "value": f"{float(metrics['min_score_to_pass']):.6g}",
            },
        )
    if "failure_reason_code" in metrics:
        rows.append(
            {
                "field": "Failure reason code",
                "value": str(metrics["failure_reason_code"]),
            },
        )
    if "latest_score_minus_min_pass" in metrics:
        rows.append(
            {
                "field": "Score minus min pass",
                "value": str(metrics["latest_score_minus_min_pass"]),
            },
        )
    if "score_meets_min_numeric" in metrics:
        rows.append(
            {
                "field": "Score >= min pass (numeric only)",
                "value": str(metrics["score_meets_min_numeric"]),
            },
        )
    if "bundle_compatibility_ranking_count" in metrics:
        rows.append(
            {
                "field": "Compatibility ranking count",
                "value": str(metrics["bundle_compatibility_ranking_count"]),
            },
        )
    if "selected_bundle_rank" in metrics:
        rows.append(
            {
                "field": "Selected bundle rank",
                "value": str(metrics["selected_bundle_rank"]),
            },
        )
    return rows


def integrator_gate_delta_operator_metrics(
    delta: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if not delta:
        return {"present": False}
    sd = _optional_float(delta.get("integrator_score_delta"))
    direction: str | None = None
    if sd is not None:
        if sd > 1e-9:
            direction = "up"
        elif sd < -1e-9:
            direction = "down"
        else:
            direction = "flat"
    pv = delta.get("previous_verdict")
    cv = delta.get("current_verdict")
    flip = None
    if pv is not None or cv is not None:
        flip = f"{pv!s} -> {cv!s}"
    return {
        "present": True,
        "score_delta_direction": direction,
        "integrator_score_delta": sd,
        "verdict_changed": bool(delta.get("verdict_changed"))
        if "verdict_changed" in delta
        else None,
        "bundle_id_changed": bool(delta.get("bundle_id_changed"))
        if "bundle_id_changed" in delta
        else None,
        "verdict_transition": flip,
    }


def integrator_gate_delta_bundle_changed_caption(
    delta: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(delta, Mapping):
        return None
    raw = delta.get("bundle_id_changed")
    if isinstance(raw, bool):
        return f"Integrator gate delta: bundle_id_changed **{str(raw).lower()}**."
    return None


def integrator_gate_delta_verdict_changed_caption(
    delta: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(delta, Mapping):
        return None
    raw = delta.get("verdict_changed")
    if isinstance(raw, bool):
        return f"Integrator gate delta: verdict_changed **{str(raw).lower()}**."
    return None


def integrator_gate_delta_operator_metrics_caption(
    metrics: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(metrics, Mapping) or metrics.get("present") is not True:
        return None
    parts: list[str] = []
    vt = metrics.get("verdict_transition")
    if isinstance(vt, str) and vt.strip():
        parts.append(f"verdict {vt}")
    direction = metrics.get("score_delta_direction")
    sd = metrics.get("integrator_score_delta")
    if direction is not None and sd is not None:
        parts.append(f"score {direction} ({sd:+.6g})")
    elif direction is not None:
        parts.append(f"score {direction}")
    if metrics.get("bundle_id_changed") is True:
        parts.append("bundle id changed")
    if not parts:
        return (
            "Integrator gate delta operator metrics: present "
            "(no score or verdict transition to summarize)."
        )
    return "Integrator gate delta operator metrics: " + "; ".join(parts) + "."


def integrator_gate_delta_transition_caption(
    delta: Mapping[str, Any] | None,
) -> str | None:
    return integrator_gate_delta_operator_metrics_caption(
        integrator_gate_delta_operator_metrics(delta),
    )


def integrator_gate_delta_operator_table_rows(
    metrics: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    if not metrics or not metrics.get("present"):
        return []
    rows: list[dict[str, str]] = []
    if metrics.get("score_delta_direction") is not None:
        rows.append(
            {
                "field": "Score delta direction",
                "value": str(metrics["score_delta_direction"]),
            },
        )
    if metrics.get("integrator_score_delta") is not None:
        rows.append(
            {
                "field": "Score delta (raw)",
                "value": str(metrics["integrator_score_delta"]),
            },
        )
    if metrics.get("verdict_changed") is not None:
        rows.append(
            {
                "field": "Verdict changed",
                "value": str(metrics["verdict_changed"]),
            },
        )
    if metrics.get("bundle_id_changed") is not None:
        rows.append(
            {
                "field": "Bundle id changed",
                "value": str(metrics["bundle_id_changed"]),
            },
        )
    vt = metrics.get("verdict_transition")
    if vt:
        rows.append({"field": "Verdict transition", "value": str(vt)})
    return rows

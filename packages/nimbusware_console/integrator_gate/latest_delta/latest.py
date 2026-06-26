from __future__ import annotations

from agent_core.coercion import is_number, is_strict_int
from collections.abc import Mapping
from typing import Any

from nimbusware_console.integrator_gate._helpers import (
    _optional_float,
    _stringify,
)


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
    if is_strict_int(ranking_count):
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
    if is_strict_int(sel_rank):
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
    n = int(count) if is_strict_int(count) else len(ranking)
    sel_rank = ig.get("selected_bundle_rank")
    sel_id = ig.get("selected_bundle_id") or ig.get("bundle_id")
    parts = [f"**{n}** catalog candidate(s) ranked by integrator score"]
    if is_strict_int(sel_rank):
        parts.append(f"selected bundle `{sel_id}` at rank **{sel_rank}**")
    elif isinstance(sel_id, str) and sel_id.strip():
        parts.append(f"selected bundle `{sel_id.strip()}`")
    top = ranking[0] if isinstance(ranking[0], dict) else None
    if top and top.get("bundle_id"):
        score = top.get("score")
        if is_number(score):
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
    if is_number(margin):
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
        is_strict_int(x) for x in (overlap, project_n, matched_n)
    ):
        return None
    if project_n == 0 and matched_n == 0 and overlap == 0:
        return None
    return f"Latest integrator gate tags: **{overlap}** matched of **{project_n}** project tag(s)."


def integrator_gate_latest_operator_metrics_caption(
    metrics: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(metrics, Mapping) or metrics.get("present") is not True:
        return None
    parts: list[str] = []
    score = metrics.get("integrator_score")
    if is_number(score):
        parts.append(f"integrator score **{float(score):.4g}**")
    min_pass = metrics.get("min_score_to_pass")
    if is_number(min_pass):
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
    if is_number(margin):
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
    if is_strict_int(n_ranked) and n_ranked > 0:
        parts.append(f"**{n_ranked}** ranked candidate(s)")
    sel_rank = metrics.get("selected_bundle_rank")
    if is_strict_int(sel_rank):
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

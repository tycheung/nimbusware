from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from agent_core.coercion import is_strict_int
from console.explainer_core.workflow_metrics_spec import (
    install_workflow_metrics_from_spec,
    repo_display_spec,
)


def _bundle_search_metrics(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    metrics: dict[str, Any] = {
        "hit_count": 0,
        "distinct_tag_count": 0,
        "hits_without_tags": 0,
        "hits_without_id": 0,
        "top_hit_id": None,
    }
    if not isinstance(payload, Mapping):
        return metrics
    hits = payload.get("hits")
    if not isinstance(hits, list):
        return metrics
    tags_seen: set[str] = set()
    hit_count = 0
    for row in hits:
        if not isinstance(row, dict):
            continue
        hit_count += 1
        bid = row.get("id")
        if not isinstance(bid, str) or not bid.strip():
            metrics["hits_without_id"] = int(metrics["hits_without_id"]) + 1
        elif metrics["top_hit_id"] is None:
            metrics["top_hit_id"] = bid.strip()
        raw_tags = row.get("tags")
        if not isinstance(raw_tags, list):
            metrics["hits_without_tags"] = int(metrics["hits_without_tags"]) + 1
            continue
        usable = [t.strip() for t in raw_tags if isinstance(t, str) and t.strip()]
        if not usable:
            metrics["hits_without_tags"] = int(metrics["hits_without_tags"]) + 1
        else:
            tags_seen.update(usable)
    metrics["hit_count"] = hit_count
    metrics["distinct_tag_count"] = len(tags_seen)
    return metrics


def _bundle_search_caption_parts(metrics: Mapping[str, Any]) -> list[str]:
    hc = metrics.get("hit_count")
    if not is_strict_int(hc) or hc < 1:
        return []
    parts = [f"**{hc}** hit(s)", f"**{metrics.get('distinct_tag_count', 0)}** distinct tag(s)"]
    wtags = metrics.get("hits_without_tags", 0)
    wid = metrics.get("hits_without_id", 0)
    if is_strict_int(wtags) and wtags > 0:
        parts.append(f"**{wtags}** without tags")
    if is_strict_int(wid) and wid > 0:
        parts.append(f"**{wid}** without id")
    return parts


_install_ns: dict[str, object] = {}
install_workflow_metrics_from_spec(
    _install_ns,
    repo_display_spec("bundle_search"),
    caption_parts_fn=_bundle_search_caption_parts,
    custom_metrics_fn=_bundle_search_metrics,
)

bundle_search_operator_metrics = _install_ns["bundle_search_operator_metrics"]
bundle_search_operator_metrics_table_rows = _install_ns["bundle_search_operator_metrics_table_rows"]
bundle_search_operator_metrics_caption = _install_ns["bundle_search_operator_metrics_caption"]
bundle_search_operator_metrics_export_json = _install_ns["bundle_search_operator_metrics_export_json"]
bundle_search_operator_metrics_table_rows_csv = _install_ns[
    "bundle_search_operator_metrics_table_rows_csv"
]
bundle_search_operator_metrics_export_filename_slug = _install_ns[
    "bundle_search_operator_metrics_export_filename_slug"
]

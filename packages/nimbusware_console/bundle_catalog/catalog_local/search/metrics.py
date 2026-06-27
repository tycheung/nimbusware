from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from agent_core.coercion import is_strict_int
from nimbusware_console.explainer_core.operator_metrics_exports import (
    install_operator_metrics_module,
    table_rows_fn,
)

_PREFIX = "bundle_search"

_DEFAULTS: dict[str, Any] = {
    "hit_count": 0,
    "distinct_tag_count": 0,
    "hits_without_tags": 0,
    "hits_without_id": 0,
    "top_hit_id": None,
}

_TABLE_ROWS: tuple[tuple[str, str], ...] = (
    ("Hit count", "hit_count"),
    ("Distinct tags (union)", "distinct_tag_count"),
    ("Hits without tags", "hits_without_tags"),
    ("Hits without id", "hits_without_id"),
    ("Top hit id", "top_hit_id"),
)


def _bundle_search_operator_metrics(
    search_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    metrics = dict(_DEFAULTS)
    if not isinstance(search_payload, Mapping):
        return metrics
    hits = search_payload.get("hits")
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


def _bundle_search_operator_metrics_table_rows(
    metrics: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    return table_rows_fn(
        _TABLE_ROWS,
        include_when=lambda _m, key: (
            key != "top_hit_id" or (isinstance(_m.get(key), str) and str(_m.get(key)).strip())
        ),
    )(metrics)


def _bundle_search_operator_metrics_caption(
    metrics: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(metrics, Mapping):
        return None
    hc = metrics.get("hit_count")
    if not is_strict_int(hc) or hc < 1:
        return None
    parts = [f"**{hc}** hit(s)", f"**{metrics.get('distinct_tag_count', 0)}** distinct tag(s)"]
    wtags = metrics.get("hits_without_tags", 0)
    wid = metrics.get("hits_without_id", 0)
    if is_strict_int(wtags) and wtags > 0:
        parts.append(f"**{wtags}** without tags")
    if is_strict_int(wid) and wid > 0:
        parts.append(f"**{wid}** without id")
    return "Bundle search operator metrics: " + ", ".join(parts) + "."


(
    bundle_search_operator_metrics,
    bundle_search_operator_metrics_table_rows,
    bundle_search_operator_metrics_caption,
    bundle_search_operator_metrics_export_json,
    bundle_search_operator_metrics_table_rows_csv,
    _bundle_search_operator_metrics_export_slug,
) = install_operator_metrics_module(
    globals(),
    module_prefix=_PREFIX,
    metrics=_bundle_search_operator_metrics,
    table_rows=_bundle_search_operator_metrics_table_rows,
    caption=_bundle_search_operator_metrics_caption,
)


def bundle_search_filename_slug(query: str, *, max_len: int = 40) -> str:
    raw = query.strip().lower().replace(" ", "_")[:max_len]
    slug = re.sub(r"[^a-z0-9_.-]+", "_", raw).strip("._-") or "query"
    return slug[:max_len]


_BUNDLE_LOCAL_CSV_COLUMNS: tuple[str, ...] = ("id", "title", "tags")

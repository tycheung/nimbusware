from __future__ import annotations

import csv
import json
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from typing import Any

from nimbusware_console.bundle_catalog.catalog_local._cells import (
    _bundle_search_hit_cell,
)

def bundle_search_operator_metrics(
    search_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    metrics: dict[str, Any] = {
        "hit_count": 0,
        "distinct_tag_count": 0,
        "hits_without_tags": 0,
        "hits_without_id": 0,
        "top_hit_id": None,
    }
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
            metrics["hits_without_id"] += 1
        elif metrics["top_hit_id"] is None:
            metrics["top_hit_id"] = bid.strip()
        raw_tags = row.get("tags")
        if not isinstance(raw_tags, list):
            metrics["hits_without_tags"] += 1
            continue
        usable = [t.strip() for t in raw_tags if isinstance(t, str) and t.strip()]
        if not usable:
            metrics["hits_without_tags"] += 1
        else:
            tags_seen.update(usable)
    metrics["hit_count"] = hit_count
    metrics["distinct_tag_count"] = len(tags_seen)
    return metrics


def bundle_search_operator_metrics_table_rows(
    metrics: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    if not isinstance(metrics, Mapping):
        return []
    rows: list[dict[str, str]] = [
        {"field": "Hit count", "value": str(metrics.get("hit_count", 0))},
        {"field": "Distinct tags (union)", "value": str(metrics.get("distinct_tag_count", 0))},
        {"field": "Hits without tags", "value": str(metrics.get("hits_without_tags", 0))},
        {"field": "Hits without id", "value": str(metrics.get("hits_without_id", 0))},
    ]
    top = metrics.get("top_hit_id")
    if isinstance(top, str) and top.strip():
        rows.append({"field": "Top hit id", "value": top.strip()})
    return rows


_BUNDLE_SEARCH_OPERATOR_METRICS_CSV_COLUMNS: tuple[str, ...] = ("field", "value")


def bundle_search_operator_metrics_export_json(
    metrics: Mapping[str, Any] | None,
) -> str:
    if not isinstance(metrics, Mapping):
        return "{}"
    return json.dumps(dict(metrics), indent=2, ensure_ascii=False)


def bundle_search_operator_metrics_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_BUNDLE_SEARCH_OPERATOR_METRICS_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow(
                {k: r.get(k, "") for k in _BUNDLE_SEARCH_OPERATOR_METRICS_CSV_COLUMNS},
            )
    return buf.getvalue()


def bundle_search_operator_metrics_export_filename_slug() -> str:
    return "bundle_search_operator_metrics"


def bundle_search_operator_metrics_caption(
    metrics: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(metrics, Mapping):
        return None
    hc = metrics.get("hit_count")
    if isinstance(hc, bool) or not isinstance(hc, int) or hc < 1:
        return None
    parts = [f"**{hc}** hit(s)", f"**{metrics.get('distinct_tag_count', 0)}** distinct tag(s)"]
    wtags = metrics.get("hits_without_tags", 0)
    wid = metrics.get("hits_without_id", 0)
    if isinstance(wtags, int) and not isinstance(wtags, bool) and wtags > 0:
        parts.append(f"**{wtags}** without tags")
    if isinstance(wid, int) and not isinstance(wid, bool) and wid > 0:
        parts.append(f"**{wid}** without id")
    return "Bundle search operator metrics: " + ", ".join(parts) + "."


def bundle_search_filename_slug(query: str, *, max_len: int = 40) -> str:
    raw = query.strip().lower().replace(" ", "_")[:max_len]
    slug = re.sub(r"[^a-z0-9_.-]+", "_", raw).strip("._-") or "query"
    return slug[:max_len]


_BUNDLE_LOCAL_CSV_COLUMNS: tuple[str, ...] = ("id", "title", "tags")



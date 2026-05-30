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

def bundle_search_top_hit_preview_caption(
    search_payload: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(search_payload, Mapping):
        return None
    hits = search_payload.get("hits")
    if not isinstance(hits, list) or not hits:
        return None
    first = hits[0]
    if not isinstance(first, dict):
        return None
    bid = first.get("id")
    if bid is None or not str(bid).strip():
        return None
    parts = [f"top hit id={str(bid).strip()!r}"]
    score = first.get("score")
    if isinstance(score, (int, float)) and not isinstance(score, bool):
        parts.append(f"score={score}")
    return "Bundle search: " + ", ".join(parts) + "."


def bundle_search_k_caption(
    search_payload: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(search_payload, Mapping):
        return None
    q = str(search_payload.get("query", "")).strip()
    if not q:
        return None
    k = search_payload.get("k")
    if not isinstance(k, int) or isinstance(k, bool) or k < 1:
        return None
    return f"Bundle search k: **{k}**."


def bundle_search_query_length_caption(
    query: str,
    *,
    hit_count: int | None = None,
) -> str | None:
    if not isinstance(query, str):
        return None
    text = query.strip()
    if not text:
        return None
    n = len(text)
    cap = f"Bundle search query: **{n}** character(s)."
    if isinstance(hit_count, int) and not isinstance(hit_count, bool) and hit_count >= 0:
        word = "hit" if hit_count == 1 else "hits"
        cap = cap[:-1] + f" (**{hit_count}** {word})."
    return cap


def bundle_search_faiss_ready_caption(
    search_payload: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(search_payload, Mapping):
        return None
    ready = search_payload.get("faiss_index_ready")
    if ready is True:
        return "Bundle search: FAISS index **ready** on the last response."
    if ready is False:
        return "Bundle search: FAISS index **not ready** on the last response."
    return None


def bundle_search_hits_summary_caption(
    search_payload: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(search_payload, Mapping):
        return None
    q = str(search_payload.get("query", "")).strip()
    if not q:
        return None
    k = search_payload.get("k")
    hits = search_payload.get("hits")
    n_hits = len(hits) if isinstance(hits, list) else 0
    parts: list[str] = [f"q={q!r}"]
    if isinstance(k, int) and not isinstance(k, bool):
        parts.append(f"k={k}")
    parts.append(f"hits={n_hits}")
    ready = search_payload.get("faiss_index_ready")
    if ready is True:
        parts.append("faiss_index_ready=yes")
    elif ready is False:
        parts.append("faiss_index_ready=no")
    stale = search_payload.get("faiss_index_stale")
    if stale is True:
        parts.append("faiss_index_stale=yes")
    elif stale is False:
        parts.append("faiss_index_stale=no")
    return "Bundle search: " + " · ".join(parts) + "."


def bundle_search_hit_count_caption(
    search_payload: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(search_payload, Mapping):
        return None
    hits = search_payload.get("hits")
    if not isinstance(hits, list) or not hits:
        return None
    n = len(hits)
    word = "hit" if n == 1 else "hits"
    return f"Bundle search: **{n}** {word}."


def bundle_search_after_hits_stale_caption(
    search_payload: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(search_payload, Mapping):
        return None
    if search_payload.get("faiss_index_stale") is not True:
        return None
    hits = search_payload.get("hits")
    if not isinstance(hits, list) or not hits:
        return None
    return (
        "FAISS index is **stale** (``catalog.yaml`` newer than ``faiss.index`` / "
        "``bundle_order.json``). Vector ordering in these hits may lag the latest catalog — "
        "rebuild from repo root (see **FAISS index readiness** above; workflow "
        f"``{BUNDLE_FAISS_INDEX_WORKFLOW_RELPATH}``)."
    )


def bundle_search_empty_hits_readiness_caption(
    search_payload: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(search_payload, Mapping):
        return None
    q = str(search_payload.get("query", "")).strip()
    if not q:
        return None
    hits = search_payload.get("hits")
    if not isinstance(hits, list) or len(hits) != 0:
        return None
    if search_payload.get("faiss_index_ready") is True:
        return (
            "Zero hits for this query with **FAISS index ready** — try a broader ``q`` or "
            "inspect tag coverage in ``configs/bundles/catalog.yaml``."
        )
    return (
        "Zero hits while **FAISS index is not ready** (``faiss.index`` + ``bundle_order.json`` "
        "missing or incomplete vs ``configs/bundles/catalog.yaml``). See **FAISS index readiness** "
        "above; workflow "
        f"``{BUNDLE_FAISS_INDEX_WORKFLOW_RELPATH}``."
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


def bundle_catalog_local_bundles(repo_root: Path) -> list[dict[str, Any]]:
    path = repo_root / "configs" / "bundles" / "catalog.yaml"
    if not path.is_file():
        return []
    import yaml

    from hermes_orchestrator.merge import load_yaml

    try:
        doc = load_yaml(path)
    except (OSError, ValueError, UnicodeDecodeError, yaml.YAMLError):
        return []
    if not isinstance(doc, dict):
        return []
    bundles = doc.get("bundles")
    if not isinstance(bundles, list):
        return []
    return [b for b in bundles if isinstance(b, dict)]


def bundle_catalog_local_bundles_table_rows(
    bundles: Sequence[Mapping[str, Any]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for b in bundles:
        if not isinstance(b, Mapping):
            continue
        rows.append(
            {
                "id": _bundle_search_hit_cell(b.get("id")),
                "title": _bundle_search_hit_cell(b.get("title")),
                "tags": _bundle_search_hit_cell(b.get("tags")),
            },
        )
    return rows


def bundle_catalog_local_bundles_export_json(
    bundles: Sequence[Mapping[str, Any]],
) -> str:
    rows = bundle_catalog_local_bundles_table_rows(bundles)
    return json.dumps(rows, indent=2, ensure_ascii=False)


def bundle_catalog_local_bundles_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_BUNDLE_LOCAL_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow({k: r.get(k, "") for k in _BUNDLE_LOCAL_CSV_COLUMNS})
    return buf.getvalue()


def bundle_catalog_local_export_filename_slug(
    repo_root: Path,
    *,
    max_len: int = 40,
) -> str:
    from nimbusware_console.bundle_catalog.faiss_status import (
        bundle_faiss_operator_drilldown_export_filename_slug,
    )

    return bundle_faiss_operator_drilldown_export_filename_slug(repo_root, max_len=max_len)


def bundle_search_hits_from_blob(blob: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(blob, Mapping):
        return []
    raw = blob.get("hits")
    if not isinstance(raw, list):
        return []
    return [h for h in raw if isinstance(h, dict)]


def bundle_search_hits_export_json(hits: Sequence[Mapping[str, Any]]) -> str:
    rows = [dict(h) for h in hits if isinstance(h, Mapping)]
    return json.dumps(rows, indent=2, ensure_ascii=False)


def _bundle_search_hit_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        parts = [str(x).strip() for x in value if isinstance(x, str) and str(x).strip()]
        return ", ".join(parts)
    if isinstance(value, (dict, tuple)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


_BUNDLE_SEARCH_HITS_CSV_COLUMNS: tuple[str, ...] = ("id", "title", "tags", "score")


def bundle_search_hits_table_rows_csv(hits: Sequence[Mapping[str, Any]]) -> str:
    if not hits:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_BUNDLE_SEARCH_HITS_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for h in hits:
        if not isinstance(h, Mapping):
            continue
        w.writerow(
            {
                "id": _bundle_search_hit_cell(h.get("id")),
                "title": _bundle_search_hit_cell(h.get("title")),
                "tags": _bundle_search_hit_cell(h.get("tags")),
                "score": _bundle_search_hit_cell(h.get("score")),
            },
        )
    return buf.getvalue()


def run_bundle_catalog_search(repo_root: Path, query: str, *, k: int) -> dict[str, Any]:
    from hermes_extensions.catalog import bundle_faiss_index_sync_state, search_bundles

    kk = max(1, min(20, int(k)))
    q = query.strip()
    sync = bundle_faiss_index_sync_state(repo_root)
    base: dict[str, Any] = {
        "query": q,
        "k": kk,
        "hits": [],
        "faiss_index_ready": bool(sync.get("ready")),
        "faiss_index_stale": sync.get("stale"),
    }
    if not q:
        return base
    hits = search_bundles(repo_root, q, k=kk)
    base["hits"] = hits
    return base

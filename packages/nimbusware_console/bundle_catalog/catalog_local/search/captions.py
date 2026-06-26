from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from agent_core.coercion import is_number, is_strict_int
from nimbusware_console.bundle_catalog.catalog_local._constants import (
    BUNDLE_FAISS_INDEX_WORKFLOW_RELPATH,
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
    if is_number(score):
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
    if is_strict_int(hit_count) and hit_count >= 0:
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
    if is_strict_int(k):
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

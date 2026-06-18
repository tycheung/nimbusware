from __future__ import annotations

import json
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from nimbusware_console.bundle_catalog.catalog_local._cells import (
    _mtime_iso_utc_ns,
)
from nimbusware_console.bundle_catalog.catalog_local._load import (
    catalog_bundle_rows,
    catalog_yaml_path,
    load_catalog_doc,
)


def _bundle_faiss_mtime_observability(sync: Mapping[str, Any]) -> dict[str, bool]:
    cat_ns = sync.get("catalog_mtime_ns")
    idx_ns = sync.get("index_max_mtime_ns")
    return {
        "catalog_mtime_observable": cat_ns is not None and not isinstance(cat_ns, bool),
        "index_mtime_observable": idx_ns is not None and not isinstance(idx_ns, bool),
    }


def _file_size_mtime(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"bytes": None, "mtime_ns": None, "mtime_iso": None}
    st = path.stat()
    return {
        "bytes": int(st.st_size),
        "mtime_ns": int(st.st_mtime_ns),
        "mtime_iso": _mtime_iso_utc_ns(int(st.st_mtime_ns)),
    }


def _catalog_bundle_row_counts(
    repo_root: Path,
    *,
    config_materializer: Any | None = None,
) -> tuple[int | None, int | None, str | None]:
    doc = load_catalog_doc(repo_root, config_materializer=config_materializer)
    if doc is None:
        if catalog_yaml_path(repo_root).is_file():
            return None, None, "catalog load failed"
        return None, None, None
    dict_rows = catalog_bundle_rows(doc)
    n_nonempty = 0
    for b in dict_rows:
        bid = b.get("id")
        if isinstance(bid, str) and bid.strip():
            n_nonempty += 1
    return len(dict_rows), n_nonempty, None


def _bundle_order_list_length(path: Path) -> tuple[int | None, str | None]:
    if not path.is_file():
        return None, None
    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as err:
        return None, str(err)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as err:
        return None, str(err)
    if not isinstance(data, list):
        return None, "bundle_order.json root is not a JSON list"
    return len(data), None


def _catalog_nonempty_stripped_id_set(
    repo_root: Path,
    *,
    config_materializer: Any | None = None,
) -> tuple[set[str] | None, str | None]:
    doc = load_catalog_doc(repo_root, config_materializer=config_materializer)
    if doc is None:
        if catalog_yaml_path(repo_root).is_file():
            return None, "catalog load failed"
        return None, None
    out: set[str] = set()
    for b in catalog_bundle_rows(doc):
        bid = b.get("id")
        if isinstance(bid, str) and bid.strip():
            out.add(bid.strip())
    return out, None


def _bundle_order_duplicate_id_signals(ids: list[str]) -> tuple[int, bool, list[str]]:
    distinct = len(set(ids))
    has_dup = len(ids) != distinct
    if not has_dup:
        return distinct, False, []
    counts = Counter(ids)
    sample = sorted(k for k, v in counts.items() if v > 1)[:8]
    return distinct, True, sample


def _parse_bundle_order_string_ids(path: Path) -> tuple[list[str] | None, str | None]:
    if not path.is_file():
        return None, None
    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as err:
        return None, str(err)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as err:
        return None, str(err)
    if not isinstance(data, list):
        return None, "bundle_order.json root is not a JSON list"
    out: list[str] = []
    for x in data:
        if not isinstance(x, str):
            return None, "bundle_order.json entry is not a string"
        t = x.strip()
        if not t:
            return None, "bundle_order.json contains empty id string"
        out.append(t)
    return out, None

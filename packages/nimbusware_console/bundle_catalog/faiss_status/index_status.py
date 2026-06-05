from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from nimbusware_console.bundle_catalog.catalog_local._cells import (
    _bundle_faiss_index_status_cell,
)
from nimbusware_console.components.operator_metrics import (
    field_value_table_rows_csv,
    mapping_to_sorted_table_rows,
)


def bundle_faiss_index_stale_caption(repo_root: Path) -> str | None:
    status = bundle_faiss_index_status(repo_root)
    ready = status.get("ready")
    if ready is False:
        return "FAISS index: **not ready** (missing faiss.index or bundle_order.json)."
    if ready is not True:
        return None
    stale = status.get("stale")
    if stale is True:
        return "FAISS index stale vs catalog: **yes** (rebuild recommended)."
    if stale is False:
        return "FAISS index stale vs catalog: **no**."
    return None


def bundle_faiss_index_status(repo_root: Path) -> dict[str, Any]:
    from nimbusware_extensions.catalog import bundle_faiss_index_sync_state

    sync = bundle_faiss_index_sync_state(repo_root)
    idx_dir = repo_root / "configs" / "bundles" / "index"
    faiss_p = idx_dir / "faiss.index"
    meta_p = idx_dir / "bundle_order.json"
    return {
        "index_dir": str(idx_dir),
        "faiss_index_path": str(faiss_p),
        "bundle_order_path": str(meta_p),
        "faiss_index_exists": faiss_p.is_file(),
        "bundle_order_exists": meta_p.is_file(),
        "ready": sync["ready"],
        "catalog_path": sync["catalog_path"],
        "catalog_exists": sync["catalog_exists"],
        "stale": sync["stale"],
        "catalog_mtime_ns": sync["catalog_mtime_ns"],
        "index_max_mtime_ns": sync["index_max_mtime_ns"],
    }


def bundle_faiss_index_status_table_rows(
    status: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    return mapping_to_sorted_table_rows(status, _bundle_faiss_index_status_cell)


def bundle_faiss_index_status_export_json(
    status: Mapping[str, Any] | None,
) -> str:
    if not isinstance(status, Mapping):
        return "{}"
    return json.dumps(dict(status), ensure_ascii=False, indent=2)


def bundle_faiss_index_status_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    return field_value_table_rows_csv(rows)

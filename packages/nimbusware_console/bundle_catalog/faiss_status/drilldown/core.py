from __future__ import annotations

import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from nimbusware_console.bundle_catalog.catalog_local.faiss_helpers import (
    _bundle_order_duplicate_id_signals,
    _bundle_order_list_length,
    _catalog_bundle_row_counts,
    _catalog_nonempty_stripped_id_set,
    _file_size_mtime,
    _parse_bundle_order_string_ids,
)
from nimbusware_console.bundle_catalog.faiss_status.index_status import (
    bundle_faiss_index_status,
)


def bundle_faiss_index_operator_drilldown(repo_root: Path) -> dict[str, Any]:
    base = dict(bundle_faiss_index_status(repo_root))
    idx_dir = Path(base["index_dir"])
    faiss_p = idx_dir / "faiss.index"
    meta_p = idx_dir / "bundle_order.json"
    base["faiss_index_file"] = _file_size_mtime(faiss_p)
    base["bundle_order_file"] = _file_size_mtime(meta_p)
    listing: list[dict[str, Any]] = []
    if idx_dir.is_dir():
        for p in sorted(idx_dir.iterdir(), key=lambda x: x.name.lower())[:25]:
            if not p.is_file():
                continue
            pr = _file_size_mtime(p)
            listing.append(
                {
                    "name": p.name,
                    "bytes": pr["bytes"],
                    "mtime_iso": pr["mtime_iso"],
                },
            )
    base["index_dir_listing"] = listing
    cat_dict_n, cat_id_n, cat_err = _catalog_bundle_row_counts(repo_root)
    base["catalog_bundle_dict_count"] = cat_dict_n
    base["catalog_bundle_nonempty_id_count"] = cat_id_n
    base["catalog_bundle_counts_load_error"] = cat_err
    ord_len, ord_err = _bundle_order_list_length(meta_p)
    base["bundle_order_list_length"] = ord_len
    base["bundle_order_parse_error"] = ord_err
    parity: bool | None = None
    if (
        cat_err is None
        and ord_err is None
        and cat_id_n is not None
        and ord_len is not None
        and meta_p.is_file()
    ):
        parity = cat_id_n == ord_len
    base["bundle_order_catalog_nonempty_id_parity"] = parity
    id_set_parity: bool | None = None
    missing_sample: list[str] = []
    extra_sample: list[str] = []
    id_set_err: str | None = None
    bundle_order_json_distinct_id_count: int | None = None
    bundle_order_json_has_duplicate_ids: bool | None = None
    bundle_order_json_duplicate_ids_sample: list[str] = []
    ord_ids: list[str] | None = None
    if ord_err is None and meta_p.is_file():
        ord_ids, oid_parse_err = _parse_bundle_order_string_ids(meta_p)
        if oid_parse_err:
            id_set_err = oid_parse_err
        if ord_ids is not None:
            (
                bundle_order_json_distinct_id_count,
                bundle_order_json_has_duplicate_ids,
                (bundle_order_json_duplicate_ids_sample),
            ) = _bundle_order_duplicate_id_signals(ord_ids)
    if cat_err is None and ord_err is None and meta_p.is_file():
        cat_set, cse = _catalog_nonempty_stripped_id_set(repo_root)
        if cse:
            id_set_err = id_set_err or cse
        if ord_ids is None:
            ord_ids, oie = _parse_bundle_order_string_ids(meta_p)
            if oie:
                id_set_err = id_set_err or oie
        if cat_set is not None and ord_ids is not None:
            ord_set = set(ord_ids)
            missing_sorted = sorted(cat_set - ord_set)
            extra_sorted = sorted(ord_set - cat_set)
            missing_sample = missing_sorted[:8]
            extra_sample = extra_sorted[:8]
            if parity is True:
                id_set_parity = cat_set == ord_set
    base["bundle_order_catalog_id_set_parity"] = id_set_parity
    base["catalog_ids_missing_from_bundle_order_sample"] = missing_sample
    base["bundle_order_ids_missing_from_catalog_sample"] = extra_sample
    base["bundle_order_catalog_id_set_load_error"] = id_set_err
    base["bundle_order_json_distinct_id_count"] = bundle_order_json_distinct_id_count
    base["bundle_order_json_has_duplicate_ids"] = bundle_order_json_has_duplicate_ids
    base["bundle_order_json_duplicate_ids_sample"] = bundle_order_json_duplicate_ids_sample
    cat_ns = base.get("catalog_mtime_ns")
    idx_ns = base.get("index_max_mtime_ns")
    catalog_index_mtime_delta_ns: int | None = None
    if type(cat_ns) is int and type(idx_ns) is int:
        catalog_index_mtime_delta_ns = cat_ns - idx_ns
    base["catalog_index_mtime_delta_ns"] = catalog_index_mtime_delta_ns
    idx_file_count = 0
    idx_subdir_count: int | None = None
    if idx_dir.is_dir():
        idx_file_count = sum(1 for p in idx_dir.iterdir() if p.is_file())
        idx_subdir_count = sum(1 for p in idx_dir.iterdir() if p.is_dir())
    base["index_dir_regular_file_count"] = idx_file_count
    base["index_dir_subdirectory_count"] = idx_subdir_count
    base["index_dir_listing_truncated"] = idx_file_count > 25 if idx_dir.is_dir() else None
    _bo_fb = base.get("bundle_order_file")
    _bo_b = _bo_fb.get("bytes") if isinstance(_bo_fb, dict) else None
    base["bundle_order_json_file_bytes"] = (
        int(_bo_b) if type(_bo_b) is int and not isinstance(_bo_b, bool) else None
    )
    from nimbusware_console.bundle_catalog.catalog_local._load import load_catalog_doc

    catalog_yaml_top_level_version_int: int | None = None
    cdoc = load_catalog_doc(repo_root)
    if isinstance(cdoc, dict):
        cver = cdoc.get("version")
        if type(cver) is int and not isinstance(cver, bool):
            catalog_yaml_top_level_version_int = cver
    base["catalog_yaml_top_level_version_int"] = catalog_yaml_top_level_version_int
    return base


def bundle_faiss_index_operator_drilldown_export_json(repo_root: Path) -> str:
    drill = bundle_faiss_index_operator_drilldown(repo_root)
    if not isinstance(drill, Mapping):
        return "{}"
    return json.dumps(dict(drill), ensure_ascii=False, indent=2)


def bundle_faiss_operator_drilldown_export_filename_slug(
    repo_root: Path,
    *,
    max_len: int = 36,
) -> str:
    try:
        name = repo_root.resolve().name
    except OSError:
        name = repo_root.name
    raw = str(name).strip().lower()
    slug = re.sub(r"[^a-z0-9_.-]+", "_", raw).strip("._-") or "repo"
    return slug[:max_len]

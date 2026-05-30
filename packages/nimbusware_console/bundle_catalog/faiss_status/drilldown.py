from __future__ import annotations

from nimbusware_console.components.operator_metrics import (
    field_value_table_rows_csv,
    mapping_export_json,
    mapping_to_sorted_table_rows,
    table_rows_csv,
)
import json
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from nimbusware_console.bundle_catalog.catalog_local._cells import (
    _bundle_faiss_index_status_cell,
    _bundle_faiss_readiness_summary_cell,
)
from nimbusware_console.bundle_catalog.catalog_local.faiss_helpers import (
    _bundle_faiss_mtime_observability,
    _bundle_order_duplicate_id_signals,
    _bundle_order_list_length,
    _catalog_bundle_row_counts,
    _catalog_nonempty_stripped_id_set,
    _file_size_mtime,
    _parse_bundle_order_string_ids,
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
            bundle_order_json_distinct_id_count, bundle_order_json_has_duplicate_ids, (
                bundle_order_json_duplicate_ids_sample
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
    base["index_dir_listing_truncated"] = (
        idx_file_count > 25 if idx_dir.is_dir() else None
    )
    _bo_fb = base.get("bundle_order_file")
    _bo_b = _bo_fb.get("bytes") if isinstance(_bo_fb, dict) else None
    base["bundle_order_json_file_bytes"] = (
        int(_bo_b) if type(_bo_b) is int and not isinstance(_bo_b, bool) else None
    )
    import yaml

    from agent_core.yaml_io import load_yaml

    catalog_yaml_top_level_version_int: int | None = None
    cat_yaml_p = repo_root / "configs" / "bundles" / "catalog.yaml"
    if cat_yaml_p.is_file():
        try:
            cdoc = load_yaml(cat_yaml_p)
            if isinstance(cdoc, dict):
                cver = cdoc.get("version")
                if type(cver) is int and not isinstance(cver, bool):
                    catalog_yaml_top_level_version_int = cver
        except (OSError, ValueError, UnicodeDecodeError, yaml.YAMLError):
            pass
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


def bundle_faiss_catalog_yaml_version_caption(repo_root: Path) -> str | None:
    raw = bundle_faiss_index_operator_drilldown(repo_root).get(
        "catalog_yaml_top_level_version_int",
    )
    if not isinstance(raw, int) or isinstance(raw, bool) or raw <= 0:
        return None
    return f"Bundle catalog YAML top-level version: **{raw}**."


def bundle_faiss_bundle_order_json_file_bytes_caption(repo_root: Path) -> str | None:
    d = bundle_faiss_index_operator_drilldown(repo_root)
    n = d.get("bundle_order_json_file_bytes")
    if type(n) is not int or isinstance(n, bool) or n < 0:
        return None
    return f"``bundle_order.json`` on disk: **{n}** byte(s) (FAISS row-order manifest)."


def bundle_faiss_catalog_order_id_set_mismatch_caption(repo_root: Path) -> str | None:
    d = bundle_faiss_index_operator_drilldown(repo_root)
    if d.get("bundle_order_catalog_id_set_parity") is not False:
        return None
    miss = d.get("catalog_ids_missing_from_bundle_order_sample") or []
    extra = d.get("bundle_order_ids_missing_from_catalog_sample") or []
    legs: list[str] = []
    if isinstance(miss, list) and miss:
        legs.append("missing in index order: " + ", ".join(str(x) for x in miss[:5]))
        if len(miss) > 5:
            legs[-1] += f" (+{len(miss) - 5} more)"
    if isinstance(extra, list) and extra:
        legs.append("extra in index order: " + ", ".join(str(x) for x in extra[:5]))
        if len(extra) > 5:
            legs[-1] += f" (+{len(extra) - 5} more)"
    tail = "; ".join(legs) if legs else "rebuild the FAISS index."
    return (
        "Catalog vs ``bundle_order.json``: **id set mismatch** (row counts match but ids "
        f"differ). {tail}"
    )


_FAISS_ID_SET_MISMATCH_CSV_COLUMNS: tuple[str, ...] = ("direction", "bundle_id")


def bundle_faiss_id_set_mismatch_table_rows(
    drilldown: Mapping[str, Any],
) -> list[dict[str, str]]:
    if not isinstance(drilldown, Mapping):
        return []
    if drilldown.get("bundle_order_catalog_id_set_parity") is not False:
        return []
    miss = drilldown.get("catalog_ids_missing_from_bundle_order_sample")
    extra = drilldown.get("bundle_order_ids_missing_from_catalog_sample")
    out: list[dict[str, str]] = []
    if isinstance(miss, list):
        for bid in miss:
            if isinstance(bid, str) and bid.strip():
                out.append(
                    {
                        "direction": "missing_from_bundle_order",
                        "bundle_id": bid.strip(),
                    },
                )
    if isinstance(extra, list):
        for bid in extra:
            if isinstance(bid, str) and bid.strip():
                out.append(
                    {
                        "direction": "extra_in_bundle_order",
                        "bundle_id": bid.strip(),
                    },
                )
    return out


def bundle_faiss_id_set_mismatch_export_json(
    rows: Sequence[Mapping[str, Any]],
) -> str:
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        return "[]"
    out: list[dict[str, Any]] = []
    for r in rows:
        if isinstance(r, Mapping):
            out.append(dict(r))
    return json.dumps(out, indent=2, ensure_ascii=False)


def bundle_faiss_id_set_mismatch_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    return table_rows_csv(rows, _FAISS_ID_SET_MISMATCH_CSV_COLUMNS)


_FAISS_DUPLICATE_ID_CSV_COLUMNS: tuple[str, ...] = ("bundle_id",)


def bundle_faiss_duplicate_id_table_rows(
    drilldown: Mapping[str, Any],
) -> list[dict[str, str]]:
    if not isinstance(drilldown, Mapping):
        return []
    if drilldown.get("bundle_order_json_has_duplicate_ids") is not True:
        return []
    sample = drilldown.get("bundle_order_json_duplicate_ids_sample")
    if not isinstance(sample, list):
        return []
    out: list[dict[str, str]] = []
    for bid in sample:
        if isinstance(bid, str) and bid.strip():
            out.append({"bundle_id": bid.strip()})
    return out


def bundle_faiss_duplicate_id_export_json(
    rows: Sequence[Mapping[str, Any]],
) -> str:
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        return "[]"
    out: list[dict[str, Any]] = []
    for r in rows:
        if isinstance(r, Mapping):
            out.append(dict(r))
    return json.dumps(out, indent=2, ensure_ascii=False)


def bundle_faiss_duplicate_id_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    return table_rows_csv(rows, _FAISS_DUPLICATE_ID_CSV_COLUMNS)


_FAISS_INDEX_DIR_LISTING_CSV_COLUMNS: tuple[str, ...] = ("name", "bytes", "mtime_iso")


def bundle_faiss_index_dir_listing_table_rows(
    drilldown: Mapping[str, Any],
) -> list[dict[str, str]]:
    if not isinstance(drilldown, Mapping):
        return []
    raw = drilldown.get("index_dir_listing")
    if not isinstance(raw, list):
        return []
    out: list[dict[str, str]] = []
    for item in raw:
        if not isinstance(item, Mapping):
            continue
        name = item.get("name")
        if not isinstance(name, str) or not name.strip():
            continue
        b = item.get("bytes")
        bytes_str = str(b) if isinstance(b, int) and not isinstance(b, bool) else ""
        mtime = item.get("mtime_iso")
        mtime_str = str(mtime).strip() if isinstance(mtime, str) else ""
        out.append(
            {
                "name": name.strip(),
                "bytes": bytes_str,
                "mtime_iso": mtime_str,
            },
        )
    return out


def bundle_faiss_index_dir_listing_export_json(
    rows: Sequence[Mapping[str, Any]],
) -> str:
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        return "[]"
    out: list[dict[str, Any]] = []
    for r in rows:
        if isinstance(r, Mapping):
            out.append(dict(r))
    return json.dumps(out, indent=2, ensure_ascii=False)


def bundle_faiss_index_dir_listing_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    return table_rows_csv(rows, _FAISS_INDEX_DIR_LISTING_CSV_COLUMNS)


def bundle_faiss_catalog_index_mtime_delta_caption(repo_root: Path) -> str | None:
    d = bundle_faiss_index_operator_drilldown(repo_root)
    if d.get("ready") is not True or d.get("catalog_exists") is not True:
        return None
    delta_ns = d.get("catalog_index_mtime_delta_ns")
    if type(delta_ns) is not int:
        return None
    sec = round(delta_ns / 1e9, 1)
    if sec > 0:
        return (
            "``catalog.yaml`` is **newer** than the FAISS index files by "
            f"**{sec:g}** s — vector search may be **stale**; rebuild the index."
        )
    if sec < 0:
        return (
            "FAISS index files are **newer** than ``catalog.yaml`` by "
            f"**{-sec:g}** s (catalog is older than the built index)."
        )
    return "``catalog.yaml`` and FAISS index files share the **same** mtime (within rounding)."


def bundle_faiss_index_dir_file_count_caption(repo_root: Path) -> str | None:
    d = bundle_faiss_index_operator_drilldown(repo_root)
    n = d.get("index_dir_regular_file_count")
    if not isinstance(n, int) or n < 0:
        return None
    return (
        "FAISS index directory (top-level): **"
        f"{n}"
        "** regular file(s); see drilldown JSON ``index_dir_regular_file_count``."
    )


def bundle_faiss_index_dir_subdirectory_count_caption(repo_root: Path) -> str | None:
    d = bundle_faiss_index_operator_drilldown(repo_root)
    n = d.get("index_dir_subdirectory_count")
    if not isinstance(n, int) or n < 0:
        return None
    return (
        "FAISS index directory (top-level): **"
        f"{n}"
        "** immediate subdirectory(ies); see drilldown JSON ``index_dir_subdirectory_count``."
    )


def bundle_faiss_index_dir_listing_truncated_caption(repo_root: Path) -> str | None:
    d = bundle_faiss_index_operator_drilldown(repo_root)
    if d.get("index_dir_listing_truncated") is not True:
        return None
    return (
        "FAISS index directory: **>25** top-level regular files — the operator drill-down "
        "``index_dir_listing`` shows at most **25** sorted file names; compare "
        "``index_dir_regular_file_count`` to the listing length."
    )


_LARGE_FAISS_INDEX_BYTES = 4 * 1024 * 1024


def bundle_faiss_index_large_file_caption(repo_root: Path) -> str | None:
    d = bundle_faiss_index_operator_drilldown(repo_root)
    fi = d.get("faiss_index_file")
    if not isinstance(fi, dict):
        return None
    b = fi.get("bytes")
    if not isinstance(b, int) or b < _LARGE_FAISS_INDEX_BYTES:
        return None
    mib = round(b / (1024 * 1024), 2)
    return (
        "``faiss.index`` on disk: **"
        f"{b}"
        "** bytes (≈ "
        f"{mib:g}"
        " MiB) — exceeds the **4 MiB** operator hint threshold; check disk space / rebuild "
        "cadence when the bundle catalog grows."
    )


def bundle_faiss_bundle_order_duplicate_ids_caption(repo_root: Path) -> str | None:
    d = bundle_faiss_index_operator_drilldown(repo_root)
    if d.get("bundle_order_json_has_duplicate_ids") is not True:
        return None
    sample = d.get("bundle_order_json_duplicate_ids_sample") or []
    nlist = d.get("bundle_order_list_length")
    ndist = d.get("bundle_order_json_distinct_id_count")
    bits: list[str] = []
    if isinstance(nlist, int) and isinstance(ndist, int):
        bits.append(f"list length {nlist}, distinct ids {ndist}")
    if isinstance(sample, list) and sample:
        vis = ", ".join(str(x) for x in sample[:5])
        if len(sample) > 5:
            vis += f" (+{len(sample) - 5} more)"
        bits.append("duplicate ids: " + vis)
    mid = "; ".join(bits) if bits else "see index listing"
    return (
        "``bundle_order.json`` contains **duplicate bundle ids** (index order is non-unique). "
        f"{mid}. Rebuild the FAISS index after fixing the catalog/build."
    )


def bundle_faiss_catalog_order_count_parity_caption(repo_root: Path) -> str | None:
    d = bundle_faiss_index_operator_drilldown(repo_root)
    if d.get("bundle_order_parse_error"):
        return None
    if d.get("catalog_bundle_counts_load_error"):
        return None
    if not d.get("bundle_order_exists"):
        return None
    if not (repo_root / "configs" / "bundles" / "catalog.yaml").is_file():
        return None
    cid = d.get("catalog_bundle_nonempty_id_count")
    olen = d.get("bundle_order_list_length")
    if not isinstance(cid, int) or not isinstance(olen, int):
        return None
    if cid == olen:
        return f"Catalog vs bundle_order.json: {cid} indexed bundle id(s) (parity)."
    return (
        f"Catalog vs bundle_order.json: **mismatch** — catalog has {cid} bundle row(s) with "
        f"non-empty ids, index lists {olen}. Rebuild the FAISS index."
    )



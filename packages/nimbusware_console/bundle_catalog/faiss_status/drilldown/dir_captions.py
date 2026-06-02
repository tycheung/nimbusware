from __future__ import annotations

from pathlib import Path

from nimbusware_console.bundle_catalog.faiss_status.drilldown.core import (
    bundle_faiss_index_operator_drilldown,
)


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

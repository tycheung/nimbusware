from __future__ import annotations

from pathlib import Path

from console.bundle_catalog.faiss_status.drilldown.core import (
    bundle_faiss_index_operator_drilldown,
)


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

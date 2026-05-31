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



from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from functools import partial
from typing import Any

from nimbusware_console.bundle_catalog.faiss_status.drilldown.captions import (
    _FAISS_ID_SET_MISMATCH_CSV_COLUMNS,
)
from nimbusware_console.components.operator_metrics import (
    table_rows_csv,
)


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


bundle_faiss_id_set_mismatch_table_rows_csv = partial(
    table_rows_csv, columns=_FAISS_ID_SET_MISMATCH_CSV_COLUMNS
)


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


bundle_faiss_duplicate_id_table_rows_csv = partial(
    table_rows_csv, columns=_FAISS_DUPLICATE_ID_CSV_COLUMNS
)


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


bundle_faiss_index_dir_listing_table_rows_csv = partial(
    table_rows_csv, columns=_FAISS_INDEX_DIR_LISTING_CSV_COLUMNS
)

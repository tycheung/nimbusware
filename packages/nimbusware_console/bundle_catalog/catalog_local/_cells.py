from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

_BUNDLE_CATALOG_LOCAL_SUMMARY_CSV_COLUMNS: tuple[str, ...] = ("field", "value")


def _bundle_catalog_local_summary_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)

_BUNDLE_CATALOG_LOCAL_SUMMARY_OPERATOR_METRICS_CSV_COLUMNS: tuple[str, ...] = (
    "field",
    "value",
)

def _bundle_faiss_readiness_summary_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _bundle_faiss_index_status_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _mtime_iso_utc_ns(mtime_ns: int) -> str:
    return datetime.fromtimestamp(mtime_ns / 1e9, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

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

from __future__ import annotations

import csv
import json
from collections.abc import Mapping, Sequence
from io import StringIO
from typing import Any


def bundle_search_hits_from_blob(blob: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(blob, Mapping):
        return []
    raw = blob.get("hits")
    if not isinstance(raw, list):
        return []
    return [h for h in raw if isinstance(h, dict)]


def bundle_search_hits_export_json(hits: Sequence[Mapping[str, Any]]) -> str:
    rows = [dict(h) for h in hits if isinstance(h, Mapping)]
    return json.dumps(rows, indent=2, ensure_ascii=False)


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


def _bundle_search_hits_csv(hits: Sequence[Mapping[str, Any]]) -> str:
    if not hits:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_BUNDLE_SEARCH_HITS_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for h in hits:
        if not isinstance(h, Mapping):
            continue
        w.writerow(
            {
                "id": _bundle_search_hit_cell(h.get("id")),
                "title": _bundle_search_hit_cell(h.get("title")),
                "tags": _bundle_search_hit_cell(h.get("tags")),
                "score": _bundle_search_hit_cell(h.get("score")),
            },
        )
    return buf.getvalue()


bundle_search_hits_table_rows_csv = _bundle_search_hits_csv

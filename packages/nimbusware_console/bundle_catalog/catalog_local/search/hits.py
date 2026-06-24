from __future__ import annotations

from collections.abc import Mapping, Sequence
from functools import partial
from typing import Any

from nimbusware_console.bundle_catalog.catalog_local._cells import (
    _bundle_search_hit_cell,
)
from nimbusware_console.components.operator_metrics import (
    sequence_export_json,
    table_rows_csv,
)

_BUNDLE_SEARCH_HITS_CSV_COLUMNS: tuple[str, ...] = ("id", "title", "tags", "score")


def bundle_search_hits_from_blob(blob: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(blob, Mapping):
        return []
    raw = blob.get("hits")
    if not isinstance(raw, list):
        return []
    return [h for h in raw if isinstance(h, dict)]


def bundle_search_hits_table_rows(
    hits: Sequence[Mapping[str, Any]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for h in hits:
        if not isinstance(h, Mapping):
            continue
        rows.append(
            {
                "id": _bundle_search_hit_cell(h.get("id")),
                "title": _bundle_search_hit_cell(h.get("title")),
                "tags": _bundle_search_hit_cell(h.get("tags")),
                "score": _bundle_search_hit_cell(h.get("score")),
            },
        )
    return rows


def bundle_search_hits_export_json(hits: Sequence[Mapping[str, Any]]) -> str:
    return sequence_export_json([dict(h) for h in hits if isinstance(h, Mapping)])


bundle_search_hits_table_rows_csv = partial(
    table_rows_csv,
    columns=_BUNDLE_SEARCH_HITS_CSV_COLUMNS,
)

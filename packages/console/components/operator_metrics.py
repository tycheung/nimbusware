from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from console.explainer_core.table_rows_csv import (
    FIELD_VALUE_COLUMNS,
    field_value_table_rows_csv,
    table_rows_csv,
)


def json_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def mapping_export_json(data: Mapping[str, Any] | None, *, empty: str = "{}") -> str:
    if not isinstance(data, Mapping):
        return empty
    return json.dumps(dict(data), indent=2, ensure_ascii=False)


def sequence_export_json(items: Sequence[Any] | None, *, empty: str = "[]") -> str:
    if items is None:
        return empty
    return json.dumps(list(items), indent=2, ensure_ascii=False)


def mapping_to_sorted_table_rows(
    data: Mapping[str, Any] | None,
    cell: Callable[[Any], str] | None = None,
) -> list[dict[str, str]]:
    if not isinstance(data, Mapping):
        return []
    fmt = cell or json_cell
    return [
        {"field": key, "value": fmt(data.get(key))} for key in sorted(str(k) for k in data.keys())
    ]


__all__ = [
    "FIELD_VALUE_COLUMNS",
    "field_value_table_rows_csv",
    "json_cell",
    "mapping_export_json",
    "mapping_to_sorted_table_rows",
    "sequence_export_json",
    "table_rows_csv",
]

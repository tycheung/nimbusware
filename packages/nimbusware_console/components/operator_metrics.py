from __future__ import annotations

import csv
import json
from collections.abc import Callable, Mapping, Sequence
from io import StringIO
from typing import Any

FIELD_VALUE_COLUMNS: tuple[str, ...] = ("field", "value")


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
        {"field": key, "value": fmt(data.get(key))}
        for key in sorted(str(k) for k in data.keys())
    ]


def table_rows_csv(
    rows: Sequence[Mapping[str, str]],
    columns: Sequence[str],
) -> str:
    if not rows:
        return ""
    buf = StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(columns), extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        if isinstance(row, Mapping):
            writer.writerow({k: row.get(k, "") for k in columns})
    return buf.getvalue()


def field_value_table_rows_csv(rows: Sequence[Mapping[str, str]]) -> str:
    return table_rows_csv(rows, FIELD_VALUE_COLUMNS)

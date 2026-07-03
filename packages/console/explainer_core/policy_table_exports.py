from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

from console.components.operator_metrics import table_rows_csv


def string_list_table_rows(
    raw: Any,
    *,
    column_name: str,
) -> list[dict[str, str]]:
    if not isinstance(raw, list):
        return []
    out: list[dict[str, str]] = []
    for key in raw:
        if isinstance(key, str) and key.strip():
            out.append({column_name: key.strip()})
    return out


def mapping_rows_export_json(rows: Sequence[Mapping[str, Any]]) -> str:
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        return "[]"
    out: list[dict[str, Any]] = []
    for row in rows:
        if isinstance(row, Mapping):
            out.append(dict(row))
    return json.dumps(out, indent=2, ensure_ascii=False)


def mapping_rows_csv(
    rows: Sequence[Mapping[str, str]],
    columns: Sequence[str],
) -> str:
    return table_rows_csv(rows, columns)

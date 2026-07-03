from __future__ import annotations

import csv
from collections.abc import Mapping, Sequence
from io import StringIO

FIELD_VALUE_COLUMNS: tuple[str, ...] = ("field", "value")


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

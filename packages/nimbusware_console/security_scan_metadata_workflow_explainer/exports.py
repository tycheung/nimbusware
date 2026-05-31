from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

from nimbusware_console.components.operator_metrics import (
    FIELD_VALUE_COLUMNS,
    field_value_table_rows_csv,
    mapping_export_json,
    mapping_to_sorted_table_rows,
)


def security_scan_metadata_export_filename_slug() -> str:
    return "security_scan_metadata"



def _security_scan_metadata_explainer_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def security_scan_metadata_explainer_table_rows(
    payload: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    return mapping_to_sorted_table_rows(payload, _security_scan_metadata_explainer_cell)


_SECURITY_SCAN_METADATA_EXPLAINER_CSV_COLUMNS = FIELD_VALUE_COLUMNS
_SECURITY_SCAN_METADATA_WORKFLOW_EXPLAINER_OPERATOR_METRICS_CSV_COLUMNS = FIELD_VALUE_COLUMNS


def security_scan_metadata_explainer_export_json(
    payload: Mapping[str, Any] | None,
) -> str:
    return mapping_export_json(payload)


def security_scan_metadata_explainer_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    return field_value_table_rows_csv(rows)




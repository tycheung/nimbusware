from __future__ import annotations

from collections.abc import Mapping, Sequence

from nimbusware_console.components.operator_metrics import FIELD_VALUE_COLUMNS
from nimbusware_console.explainer_core.workflow_exports import (
    explainer_json_cell,
    workflow_explainer_payload_export_json,
    workflow_explainer_payload_table_rows,
    workflow_explainer_payload_table_rows_csv,
)

_security_scan_metadata_explainer_cell = explainer_json_cell


def security_scan_metadata_export_filename_slug() -> str:
    return "security_scan_metadata"


def security_scan_metadata_explainer_table_rows(
    payload: Mapping[str, object] | None,
) -> list[dict[str, str]]:
    return workflow_explainer_payload_table_rows(payload)


_SECURITY_SCAN_METADATA_EXPLAINER_CSV_COLUMNS = FIELD_VALUE_COLUMNS
_SECURITY_SCAN_METADATA_WORKFLOW_EXPLAINER_OPERATOR_METRICS_CSV_COLUMNS = FIELD_VALUE_COLUMNS


def security_scan_metadata_explainer_export_json(payload: Mapping[str, object] | None) -> str:
    return workflow_explainer_payload_export_json(payload)


def security_scan_metadata_explainer_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    return workflow_explainer_payload_table_rows_csv(rows)

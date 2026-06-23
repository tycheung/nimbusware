from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

from nimbusware_console.components.operator_metrics import (
    mapping_export_json,
    mapping_to_sorted_table_rows,
)
from nimbusware_console.explainer_core.table_rows_csv import field_value_table_rows_csv


def explainer_json_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def workflow_explainer_payload_table_rows(
    payload: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    return mapping_to_sorted_table_rows(payload, explainer_json_cell)


def workflow_explainer_payload_export_json(payload: Mapping[str, Any] | None) -> str:
    return mapping_export_json(payload)


def workflow_explainer_payload_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    return field_value_table_rows_csv(rows)


class WorkflowExplainerExports:
    def __init__(self, slug: str) -> None:
        self.slug = slug
        self.cell = explainer_json_cell

    def export_filename_slug(self) -> str:
        return self.slug

    def explainer_table_rows(self, payload: Mapping[str, object] | None) -> list[dict[str, str]]:
        return workflow_explainer_payload_table_rows(payload)

    def explainer_export_json(self, payload: Mapping[str, object] | None) -> str:
        return workflow_explainer_payload_export_json(payload)

    def explainer_table_rows_csv(self, rows: Sequence[Mapping[str, str]]) -> str:
        return workflow_explainer_payload_table_rows_csv(rows)


def install_named_workflow_explainer_exports(
    namespace: dict[str, object],
    slug: str,
    *,
    cell_alias: str | None = None,
) -> WorkflowExplainerExports:
    exports = WorkflowExplainerExports(slug)
    prefix = slug
    namespace[cell_alias or f"_{prefix}_explainer_cell"] = exports.cell
    namespace[f"{prefix}_export_filename_slug"] = exports.export_filename_slug
    namespace[f"{prefix}_explainer_table_rows"] = exports.explainer_table_rows
    namespace[f"{prefix}_explainer_export_json"] = exports.explainer_export_json
    namespace[f"{prefix}_explainer_table_rows_csv"] = exports.explainer_table_rows_csv
    return exports

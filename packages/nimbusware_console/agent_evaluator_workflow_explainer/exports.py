from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

from nimbusware_console.components.operator_metrics import (
    field_value_table_rows_csv,
    mapping_export_json,
    mapping_to_sorted_table_rows,
)


def agent_evaluator_export_filename_slug() -> str:
    return "agent_evaluator"


def _agent_evaluator_explainer_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def agent_evaluator_explainer_table_rows(
    payload: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    return mapping_to_sorted_table_rows(payload, _agent_evaluator_explainer_cell)


def agent_evaluator_explainer_export_json(
    payload: Mapping[str, Any] | None,
) -> str:
    return mapping_export_json(payload)


def agent_evaluator_explainer_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    return field_value_table_rows_csv(rows)

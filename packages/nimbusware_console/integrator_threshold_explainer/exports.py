from __future__ import annotations

from nimbusware_console.components.operator_metrics import (
    FIELD_VALUE_COLUMNS,
    field_value_table_rows_csv,
    mapping_export_json,
    mapping_to_sorted_table_rows,
    sequence_export_json,
    table_rows_csv,
)
import json
import os
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from nimbusware_console.config_materializer import console_config_materializer
from nimbusware_console.integrator_workflow_preview import (
    parse_integrator_gate_yaml_fragment,
    preview_effective_min_score_to_pass,
)
from hermes_orchestrator.integrator_gate import (
    effective_integrator_min_score_to_pass,
    integrator_gate_workflow_enabled,
    load_integrator_gate_emit_enabled,
    load_integrator_gate_workflow_block,
    parse_integrator_gate_min_score_to_pass,
    parse_integrator_gate_project_tags,
)
from nimbusware_config.workflow_read import (
    load_yaml,
    workflow_profile_path,
)
from nimbusware_console.components.workflow_explainer_helpers import relative_under

def integrator_threshold_export_filename_slug() -> str:
    return "integrator_threshold"



def _integrator_threshold_explainer_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def integrator_threshold_explainer_table_rows(
    payload: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    return mapping_to_sorted_table_rows(payload, _integrator_threshold_explainer_cell)


def integrator_threshold_explainer_export_json(
    payload: Mapping[str, Any] | None,
) -> str:
    return mapping_export_json(payload)


def integrator_threshold_explainer_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    return field_value_table_rows_csv(rows)




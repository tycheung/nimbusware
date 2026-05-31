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
from collections.abc import Mapping, Sequence
from dataclasses import asdict
from pathlib import Path
from typing import Any

from nimbusware_console.config_materializer import console_config_materializer
from nimbusware_console.explainer_workflow_disk import load_workflow_profile_documents
from nimbusware_config.workflow_read import (
    effective_universal_critique,
    parse_universal_critique_workflow_block,
    workflow_profile_path,
)


from nimbusware_console.components.workflow_explainer_helpers import relative_under


def _universal_critique_yaml_value_nonempty(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return True
    if isinstance(value, (int, float)):
        return True
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return len(value) > 0
    if isinstance(value, dict):
        return len(value) > 0
    return True


def _universal_critique_top_level_nonempty_count(uc: Mapping[str, Any]) -> int:
    return sum(1 for v in uc.values() if _universal_critique_yaml_value_nonempty(v))


def _universal_critique_top_level_enabled_true_count(uc: Mapping[str, Any]) -> int:
    return sum(
        1 for v in uc.values() if isinstance(v, dict) and v.get("enabled") is True
    )


def _universal_critique_top_level_enabled_false_count(uc: Mapping[str, Any]) -> int:
    return sum(
        1 for v in uc.values() if isinstance(v, dict) and v.get("enabled") is False
    )


def _universal_critique_top_level_mapping_child_count(uc: Mapping[str, Any]) -> int:
    return sum(1 for v in uc.values() if isinstance(v, dict))


def _universal_critique_top_level_scalar_leaf_count(uc: Mapping[str, Any]) -> int:
    return sum(1 for v in uc.values() if not isinstance(v, (dict, list)))


def _universal_critique_top_level_list_child_count(uc: Mapping[str, Any]) -> int:
    return sum(1 for v in uc.values() if isinstance(v, list))


def _universal_critique_top_level_enabled_unset_mapping_count(uc: Mapping[str, Any]) -> int:
    return sum(
        1 for v in uc.values() if isinstance(v, dict) and "enabled" not in v
    )



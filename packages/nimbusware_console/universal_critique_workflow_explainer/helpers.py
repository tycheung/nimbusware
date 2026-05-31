from __future__ import annotations

from collections.abc import Mapping
from typing import Any


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



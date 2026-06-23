from __future__ import annotations

from collections.abc import Mapping, Sequence
from functools import partial
from typing import Any

from agent_core.mapping import field_error_text
from nimbusware_console.explainer_core.policy_table_exports import (
    mapping_rows_csv,
    mapping_rows_export_json,
    string_list_table_rows,
)

_POLICY_KEYS_CSV_COLUMNS: tuple[str, ...] = ("policy_key",)

_POLICY_KINDS_CSV_COLUMNS: tuple[str, ...] = ("kind", "count")

_POLICY_KINDS_ORDER: tuple[str, ...] = ("mapping", "scalar", "list", "other")


def _escalation_policy_keys_rows_from_list(raw: Any) -> list[dict[str, str]]:
    return string_list_table_rows(raw, column_name="policy_key")


def escalation_policy_yaml_keys_all_table_rows(
    payload: Mapping[str, Any],
) -> list[dict[str, str]]:
    if not isinstance(payload, Mapping):
        return []
    full = payload.get("escalation_policy_yaml_top_level_keys")
    if isinstance(full, list) and full:
        return _escalation_policy_keys_rows_from_list(full)
    return _escalation_policy_keys_rows_from_list(
        payload.get("escalation_policy_yaml_top_level_keys_sample"),
    )


def escalation_policy_yaml_keys_all_export_json(
    rows: Sequence[Mapping[str, Any]],
) -> str:
    return mapping_rows_export_json(rows)


escalation_policy_yaml_keys_all_table_rows_csv = partial(
    mapping_rows_csv, columns=_POLICY_KEYS_CSV_COLUMNS
)


def escalation_policy_yaml_top_level_kinds_table_rows(
    payload: Mapping[str, Any],
) -> list[dict[str, str]]:
    if not isinstance(payload, Mapping):
        return []
    if payload.get("escalation_policy_yaml_path_exists") is not True:
        return []
    if field_error_text(payload, "escalation_policy_yaml_load_error") is not None:
        return []
    kinds = payload.get("escalation_policy_yaml_top_level_kinds")
    if not isinstance(kinds, Mapping):
        return []

    def _count(key: str) -> int:
        raw = kinds.get(key)
        if isinstance(raw, bool) or not isinstance(raw, int):
            return 0
        return max(raw, 0)

    mapping_n = _count("mapping")
    scalar_n = _count("scalar")
    list_n = _count("list")
    other_n = _count("other")
    if (mapping_n + scalar_n + list_n + other_n) == 0:
        return []
    return [{"kind": kind, "count": str(_count(kind))} for kind in _POLICY_KINDS_ORDER]


def escalation_policy_yaml_top_level_kinds_export_json(
    rows: Sequence[Mapping[str, Any]],
) -> str:
    return mapping_rows_export_json(rows)


escalation_policy_yaml_top_level_kinds_table_rows_csv = partial(
    mapping_rows_csv, columns=_POLICY_KINDS_CSV_COLUMNS
)

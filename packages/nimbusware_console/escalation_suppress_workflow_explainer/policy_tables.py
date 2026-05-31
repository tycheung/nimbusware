from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

from nimbusware_console.components.operator_metrics import (
    table_rows_csv,
)

_POLICY_KEYS_CSV_COLUMNS: tuple[str, ...] = ("policy_key",)

_POLICY_KINDS_CSV_COLUMNS: tuple[str, ...] = ("kind", "count")

_POLICY_KINDS_ORDER: tuple[str, ...] = ("mapping", "scalar", "list", "other")


def _escalation_policy_keys_rows_from_list(raw: Any) -> list[dict[str, str]]:
    if not isinstance(raw, list):
        return []
    out: list[dict[str, str]] = []
    for key in raw:
        if isinstance(key, str) and key.strip():
            out.append({"policy_key": key.strip()})
    return out


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
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        return "[]"
    out: list[dict[str, Any]] = []
    for r in rows:
        if isinstance(r, Mapping):
            out.append(dict(r))
    return json.dumps(out, indent=2, ensure_ascii=False)


def escalation_policy_yaml_keys_all_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    return table_rows_csv(rows, _POLICY_KEYS_CSV_COLUMNS)


def escalation_policy_yaml_top_level_kinds_table_rows(
    payload: Mapping[str, Any],
) -> list[dict[str, str]]:
    if not isinstance(payload, Mapping):
        return []
    if payload.get("escalation_policy_yaml_path_exists") is not True:
        return []
    load_err = payload.get("escalation_policy_yaml_load_error")
    if isinstance(load_err, str) and load_err.strip():
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
    return [
        {"kind": kind, "count": str(_count(kind))}
        for kind in _POLICY_KINDS_ORDER
    ]


def escalation_policy_yaml_top_level_kinds_export_json(
    rows: Sequence[Mapping[str, Any]],
) -> str:
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        return "[]"
    out: list[dict[str, Any]] = []
    for r in rows:
        if isinstance(r, Mapping):
            out.append(dict(r))
    return json.dumps(out, indent=2, ensure_ascii=False)


def escalation_policy_yaml_top_level_kinds_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    return table_rows_csv(rows, _POLICY_KINDS_CSV_COLUMNS)

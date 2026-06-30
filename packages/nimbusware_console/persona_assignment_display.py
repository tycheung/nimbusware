from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from functools import partial
from typing import Any

from nimbusware_console.components.operator_metrics import field_value_table_rows_csv
from nimbusware_console.explainer_core.display_common import stringify_display_value as _stringify

_PERSONA_ASSIGNMENT_FIELDS: tuple[tuple[str, str], ...] = (
    ("business_area.id", "Business area id"),
    ("business_area.display_name", "Business area display name"),
    ("development_role.id", "Development role id"),
    ("development_role.display_name", "Development role display name"),
)


def persona_assignment_from_timeline(
    timeline_body: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(timeline_body, Mapping):
        return None
    raw = timeline_body.get("persona_assignment")
    return raw if isinstance(raw, dict) else None


def persona_assignment_summary_rows(
    pa: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    if not isinstance(pa, Mapping):
        return []
    rows: list[dict[str, str]] = []
    ba = pa.get("business_area")
    if isinstance(ba, dict):
        if "id" in ba:
            rows.append(
                {
                    "field": "Business area id",
                    "value": _stringify(ba.get("id")),
                },
            )
        if ba.get("display_name") is not None:
            rows.append(
                {
                    "field": "Business area display name",
                    "value": _stringify(ba.get("display_name")),
                },
            )
    dr = pa.get("development_role")
    if isinstance(dr, dict):
        if "id" in dr:
            rows.append(
                {
                    "field": "Development role id",
                    "value": _stringify(dr.get("id")),
                },
            )
        if dr.get("display_name") is not None:
            rows.append(
                {
                    "field": "Development role display name",
                    "value": _stringify(dr.get("display_name")),
                },
            )
    return rows


def persona_assignment_caption(pa: Mapping[str, Any] | None) -> str | None:
    if not isinstance(pa, Mapping):
        return None
    parts: list[str] = []
    ba = pa.get("business_area")
    if isinstance(ba, dict) and isinstance(ba.get("id"), str) and ba["id"].strip():
        parts.append(f"business_area={ba['id'].strip()!r}")
    dr = pa.get("development_role")
    if isinstance(dr, dict) and isinstance(dr.get("id"), str) and dr["id"].strip():
        parts.append(f"development_role={dr['id'].strip()!r}")
    if not parts:
        return None
    return "Persona assignment: " + ", ".join(parts) + "."


persona_assignment_timeline_table_rows_csv = field_value_table_rows_csv


def persona_assignment_timeline_export_json(pa: Mapping[str, Any] | None) -> str:
    return json.dumps(pa if isinstance(pa, Mapping) else {}, ensure_ascii=False, indent=2)

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any


def stringify_display_value(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def display_mapping_export_json(payload: Mapping[str, Any] | None, *, indent: int = 2) -> str:
    return json.dumps(
        payload if isinstance(payload, Mapping) else {}, ensure_ascii=False, indent=indent
    )

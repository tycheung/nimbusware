from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from agent_core.mapping import load_error_text


def workflow_yaml_version_caption(
    payload: Mapping[str, Any] | None,
    *,
    label: str,
) -> str | None:
    if not isinstance(payload, Mapping):
        return None
    if load_error_text(payload) is not None:
        return None
    raw = payload.get("workflow_yaml_top_level_version_int")
    if not isinstance(raw, int) or isinstance(raw, bool) or raw <= 0:
        return None
    return f"{label} workflow YAML top-level version: **{raw}**."

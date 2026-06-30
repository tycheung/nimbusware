from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from nimbusware_console.explainer_core.display_common import stringify_display_value as _stringify
from nimbusware_projections.fields.integrator_gate import INTEGRATOR_GATE_DISPLAY_FIELDS

_INTEGRATOR_GATE_FIELDS = INTEGRATOR_GATE_DISPLAY_FIELDS


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def integrator_gate_from_timeline(timeline_body: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(timeline_body, Mapping):
        return None
    raw = timeline_body.get("integrator_gate")
    return raw if isinstance(raw, dict) else None


def integrator_gate_history_from_timeline(
    timeline_body: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    if not isinstance(timeline_body, Mapping):
        return []
    raw = timeline_body.get("integrator_gate_history")
    if not isinstance(raw, list):
        return []
    return [x for x in raw if isinstance(x, dict)]


def _format_tag_list_sample(tags: Any, *, max_n: int = 3) -> str:
    if not isinstance(tags, list):
        return "—"
    usable: list[str] = []
    for t in tags:
        if isinstance(t, str) and t.strip():
            usable.append(t.strip())
    if not usable:
        return "—"
    usable = sorted(set(usable))
    if len(usable) <= max_n:
        return ", ".join(usable)
    extra = len(usable) - max_n
    return ", ".join(usable[:max_n]) + f", +{extra} more"

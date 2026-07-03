from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from agent_core.coercion import is_strict_int

NO_TIMELINE = "—"


def version_as_optional_int(value: Any) -> int | None:
    if is_strict_int(value):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def env_override_delta_rows(
    payload: Mapping[str, Any],
    *,
    yaml_only_key: str = "yaml_only",
    effective_key: str = "effective_with_env",
    knob_column: str = "knob",
    yaml_column: str = "yaml_only",
    effective_column: str = "effective_with_env",
) -> list[dict[str, str]]:
    yo = payload.get(yaml_only_key)
    eff = payload.get(effective_key)
    if not isinstance(yo, dict) or not isinstance(eff, dict):
        return []
    rows: list[dict[str, str]] = []
    for k in sorted(yo.keys()):
        if k not in eff:
            continue
        yv, ev = yo[k], eff[k]
        if yv != ev:
            rows.append(
                {
                    knob_column: k,
                    yaml_column: str(yv),
                    effective_column: str(ev),
                },
            )
    return rows


def timeline_present_caption(timeline: Mapping[str, Any] | None) -> str:
    if timeline is None:
        return NO_TIMELINE
    if timeline:
        return "snapshot present"
    return "(empty object)"


def timeline_int_field(
    timeline: Mapping[str, Any] | None,
    field: str,
) -> str:
    if timeline is None:
        return NO_TIMELINE
    raw = timeline.get(field)
    if not isinstance(raw, int) or isinstance(raw, bool):
        return "—"
    return str(raw)


def version_alignment_note(
    *,
    explainer_version: Any,
    timeline_version: Any,
    timeline_absent: bool,
) -> str:
    if timeline_absent:
        return NO_TIMELINE
    expl_i = version_as_optional_int(explainer_version)
    tl_i = version_as_optional_int(timeline_version)
    if expl_i is None or tl_i is None:
        return "n/a (need integer-like versions on both sides)"
    if expl_i == tl_i:
        return "match"
    return f"mismatch (explainer {expl_i} vs timeline {tl_i})"

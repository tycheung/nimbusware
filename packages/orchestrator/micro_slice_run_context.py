from __future__ import annotations

from typing import Any

from agent_core.mapping import mapping_or_empty
from agent_core.models import EventType
from orchestrator.fast_slice_critique import fast_slice_env_effective
from orchestrator.slice_diff import slice_replan_max_attempts


def run_created_metadata(rows: list[dict[str, Any]]) -> dict[str, Any]:
    for row in rows:
        if row.get("event_type") != EventType.RUN_CREATED.value:
            continue
        return mapping_or_empty(row.get("metadata"))
    return {}


def fast_slice_effective_from_rows(rows: list[dict[str, Any]]) -> bool:
    from orchestrator.enforcement_pipeline import active_enforcement_profile

    profile = active_enforcement_profile(rows)
    if profile is not None and not profile.fast_slice_allowed:
        return False
    fs = mapping_or_empty(run_created_metadata(rows).get("fast_slice_effective"))
    if not fs:
        return False
    return fast_slice_env_effective(yaml_enabled=bool(fs.get("enabled")))


def micro_slice_effective_from_rows(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    ms = mapping_or_empty(run_created_metadata(rows).get("micro_slice_effective"))
    if ms.get("enabled"):
        return ms
    return None


def slice_replan_max_for_run(rows: list[dict[str, Any]]) -> int:
    ms = micro_slice_effective_from_rows(rows)
    if ms and "replan_max" in ms:
        return max(0, min(10, int(ms["replan_max"])))
    return slice_replan_max_attempts()

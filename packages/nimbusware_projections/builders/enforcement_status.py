from __future__ import annotations

from typing import Any

from agent_core.mapping import mapping_or_empty


def enforcement_status_from_events(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not events:
        return None
    from nimbusware_orchestrator.enforcement_profiles import (
        enforcement_profile_from_rows,
        latest_enforcement_block_from_rows,
    )

    if latest_enforcement_block_from_rows(events) is None:
        meta = mapping_or_empty(
            next(
                (r.get("metadata") for r in events if r.get("event_type") == "run.created"),
                {},
            ),
        )
        if not mapping_or_empty(meta.get("enforcement_effective")).get("level"):
            return None

    profile = enforcement_profile_from_rows(events)
    gate_passed: bool | None = None
    for row in reversed(events):
        payload = mapping_or_empty(row.get("payload"))
        if payload.get("stage_name") != "enforcement.gate":
            continue
        et = str(row.get("event_type") or "")
        if et == "stage.passed":
            gate_passed = True
        elif et == "stage.failed":
            gate_passed = False
        break

    out: dict[str, Any] = {"level": profile.level, "name": profile.name}
    if gate_passed is not None:
        out["gate_passed"] = gate_passed
    return out

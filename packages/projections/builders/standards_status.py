from __future__ import annotations

from typing import Any

from agent_core.mapping import mapping_or_empty
from standards.persist import latest_standards_block_from_rows


def standards_status_from_events(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    block = latest_standards_block_from_rows(events)
    if block is None:
        return None
    gate_passed: bool | None = None
    for row in reversed(events):
        payload = mapping_or_empty(row.get("payload"))
        if payload.get("stage_name") != "slice.standards":
            continue
        meta = mapping_or_empty(row.get("metadata"))
        steps = meta.get("slice_gate_steps")
        if isinstance(steps, list):
            for step in steps:
                if isinstance(step, dict) and step.get("name") == "slice.standards":
                    verdict = str(step.get("verdict") or "").upper()
                    if verdict == "PASS":
                        gate_passed = True
                    elif verdict == "FAIL":
                        gate_passed = False
                    break
        break
    out: dict[str, Any] = {
        "facade_id": block.get("facade_id"),
        "bundle_ids": block.get("bundle_ids") or [],
        "connector_ids": block.get("connector_ids") or [],
    }
    if gate_passed is not None:
        out["gate_passed"] = gate_passed
    return out

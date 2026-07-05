from __future__ import annotations

from typing import Any

from agent_core.mapping import mapping_or_empty


def latest_stage_metadata(
    events: list[dict[str, Any]],
    stage_name: str,
) -> dict[str, Any] | None:
    for row in reversed(events):
        payload = mapping_or_empty(row.get("payload"))
        if str(payload.get("stage_name") or "") != stage_name:
            continue
        meta = mapping_or_empty(row.get("metadata"))
        return meta or None
    return None


def collect_stage_metadata(
    events: list[dict[str, Any]],
    stage_name: str,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in events:
        payload = mapping_or_empty(row.get("payload"))
        if str(payload.get("stage_name") or "") != stage_name:
            continue
        meta = mapping_or_empty(row.get("metadata"))
        if meta:
            out.append(meta)
    return out


def metadata_chain(events: list[dict[str, Any]], *keys: str) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for key in keys:
        for row in reversed(events):
            meta = mapping_or_empty(row.get("metadata"))
            block = mapping_or_empty(meta.get(key))
            if block:
                merged = {**merged, **block}
                break
    return merged

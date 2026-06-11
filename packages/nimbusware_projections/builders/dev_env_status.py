from __future__ import annotations

from typing import Any


def dev_env_status_from_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    latest: dict[str, Any] | None = None
    for row in reversed(rows):
        meta = row.get("metadata")
        if not isinstance(meta, dict):
            continue
        block = meta.get("dev_env")
        if not isinstance(block, dict):
            continue
        payload = row.get("payload")
        stage = payload.get("stage_name") if isinstance(payload, dict) else None
        latest = {
            "stage": stage,
            "session_id": block.get("session_id"),
            "base_url": block.get("base_url"),
            "stack": block.get("stack"),
            "health": block.get("health"),
            "adapter": block.get("adapter"),
        }
        if stage == "dev_env.stopped":
            break
    return latest or {"active": False}

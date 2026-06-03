from __future__ import annotations

import json
from typing import Any

from nimbusware_client.http import get_json, post_json

TOOL_SPECS: list[dict[str, Any]] = [
    {
        "name": "hermes_run_status",
        "description": "Fetch run summary from GET /v1/runs/{run_id}.",
        "inputSchema": {
            "type": "object",
            "properties": {"run_id": {"type": "string"}},
            "required": ["run_id"],
        },
    },
    {
        "name": "hermes_run_theater",
        "description": "Fetch plain-language theater messages for a run.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "run_id": {"type": "string"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 200},
            },
            "required": ["run_id"],
        },
    },
    {
        "name": "hermes_slice_diff",
        "description": "Fetch unified diff for a slice index.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "run_id": {"type": "string"},
                "slice_index": {"type": "integer", "minimum": 0},
            },
            "required": ["run_id", "slice_index"],
        },
    },
    {
        "name": "hermes_approve_plan",
        "description": "Approve the pending maker plan gate for a run.",
        "inputSchema": {
            "type": "object",
            "properties": {"run_id": {"type": "string"}},
            "required": ["run_id"],
        },
    },
]


def _text_result(payload: Any) -> dict[str, Any]:
    text = json.dumps(payload, indent=2, default=str)
    return {"content": [{"type": "text", "text": text}]}


def call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    run_id = str(arguments.get("run_id") or "").strip()
    if not run_id:
        raise ValueError("run_id is required")
    if name == "hermes_run_status":
        return _text_result(get_json(f"/runs/{run_id}"))
    if name == "hermes_run_theater":
        limit = int(arguments.get("limit") or 50)
        return _text_result(
            get_json(f"/runs/{run_id}/theater", params={"cursor": 0, "limit": limit}),
        )
    if name == "hermes_slice_diff":
        idx = int(arguments.get("slice_index"))
        return _text_result(get_json(f"/runs/{run_id}/slices/{idx}/diff"))
    if name == "hermes_approve_plan":
        return _text_result(post_json(f"/runs/{run_id}/maker/plan/approve", {}))
    raise ValueError(f"unknown tool: {name}")

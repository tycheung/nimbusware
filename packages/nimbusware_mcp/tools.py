from __future__ import annotations

import json
from typing import Any

from nimbusware_client.http import get_json, post_json

TOOL_SPECS: list[dict[str, Any]] = [
    {
        "name": "nimbusware_prepare_slice",
        "description": "Prepare the next pending slice for maker approval.",
        "inputSchema": {
            "type": "object",
            "properties": {"run_id": {"type": "string"}},
            "required": ["run_id"],
        },
    },
    {
        "name": "nimbusware_apply_slice",
        "description": "Apply a pending slice after operator approval.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "run_id": {"type": "string"},
                "slice_id": {"type": "string"},
            },
            "required": ["run_id", "slice_id"],
        },
    },
    {
        "name": "nimbusware_skip_slice",
        "description": "Skip a pending slice without applying.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "run_id": {"type": "string"},
                "slice_id": {"type": "string"},
            },
            "required": ["run_id", "slice_id"],
        },
    },
    {
        "name": "nimbusware_maker_pending",
        "description": "Fetch pending slice and plan approval state for a run.",
        "inputSchema": {
            "type": "object",
            "properties": {"run_id": {"type": "string"}},
            "required": ["run_id"],
        },
    },
    {
        "name": "nimbusware_resume_campaign",
        "description": "Resume a paused campaign.",
        "inputSchema": {
            "type": "object",
            "properties": {"campaign_id": {"type": "string"}},
            "required": ["campaign_id"],
        },
    },
    {
        "name": "nimbusware_run_status",
        "description": "Fetch run summary from GET /v1/runs/{run_id}.",
        "inputSchema": {
            "type": "object",
            "properties": {"run_id": {"type": "string"}},
            "required": ["run_id"],
        },
    },
    {
        "name": "nimbusware_run_theater",
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
        "name": "nimbusware_slice_diff",
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
        "name": "nimbusware_approve_plan",
        "description": "Approve the pending maker plan gate for a run.",
        "inputSchema": {
            "type": "object",
            "properties": {"run_id": {"type": "string"}},
            "required": ["run_id"],
        },
    },
    {
        "name": "nimbusware_campaign_status",
        "description": "Fetch campaign progress for a run/campaign id.",
        "inputSchema": {
            "type": "object",
            "properties": {"campaign_id": {"type": "string"}},
            "required": ["campaign_id"],
        },
    },
    {
        "name": "nimbusware_pause_campaign",
        "description": "Pause an active campaign.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "campaign_id": {"type": "string"},
                "reason_code": {"type": "string"},
            },
            "required": ["campaign_id"],
        },
    },
    {
        "name": "nimbusware_backlog_summary",
        "description": "Fetch delivery backlog tree summary for a campaign.",
        "inputSchema": {
            "type": "object",
            "properties": {"campaign_id": {"type": "string"}},
            "required": ["campaign_id"],
        },
    },
    {
        "name": "nimbusware_compact_run",
        "description": "Trigger campaign context compaction for a run.",
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
    if name in (
        "nimbusware_campaign_status",
        "nimbusware_pause_campaign",
        "nimbusware_backlog_summary",
        "nimbusware_resume_campaign",
    ):
        campaign_id = str(arguments.get("campaign_id") or "").strip()
        if not campaign_id:
            raise ValueError("campaign_id is required")
        if name == "nimbusware_campaign_status":
            progress = get_json(f"/runs/{campaign_id}/maker-progress")
            return _text_result(progress.get("campaign_progress") or progress)
        if name == "nimbusware_pause_campaign":
            reason = str(arguments.get("reason_code") or "mcp")
            return _text_result(
                post_json(f"/campaigns/{campaign_id}/pause", {"reason_code": reason}),
            )
        if name == "nimbusware_resume_campaign":
            return _text_result(post_json(f"/campaigns/{campaign_id}/resume", {}))
        return _text_result(get_json(f"/campaigns/{campaign_id}/backlog"))

    run_id = str(arguments.get("run_id") or "").strip()
    if not run_id:
        raise ValueError("run_id is required")
    if name == "nimbusware_maker_pending":
        return _text_result(get_json(f"/runs/{run_id}/maker/pending"))
    if name == "nimbusware_prepare_slice":
        return _text_result(post_json(f"/runs/{run_id}/maker/slices/prepare", {}))
    if name == "nimbusware_apply_slice":
        slice_id = str(arguments.get("slice_id") or "").strip()
        if not slice_id:
            raise ValueError("slice_id is required")
        return _text_result(
            post_json(f"/runs/{run_id}/maker/slices/apply", {"slice_id": slice_id}),
        )
    if name == "nimbusware_skip_slice":
        slice_id = str(arguments.get("slice_id") or "").strip()
        if not slice_id:
            raise ValueError("slice_id is required")
        return _text_result(
            post_json(f"/runs/{run_id}/maker/slices/skip", {"slice_id": slice_id}),
        )
    if name == "nimbusware_run_status":
        return _text_result(get_json(f"/runs/{run_id}"))
    if name == "nimbusware_run_theater":
        limit = int(arguments.get("limit") or 50)
        return _text_result(
            get_json(f"/runs/{run_id}/theater", params={"cursor": 0, "limit": limit}),
        )
    if name == "nimbusware_slice_diff":
        raw_idx = arguments.get("slice_index")
        if raw_idx is None:
            raise ValueError("slice_index is required")
        idx = int(raw_idx)
        return _text_result(get_json(f"/runs/{run_id}/slices/{idx}/diff"))
    if name == "nimbusware_approve_plan":
        return _text_result(post_json(f"/runs/{run_id}/maker/plan/approve", {}))
    if name == "nimbusware_compact_run":
        return _text_result(post_json(f"/runs/{run_id}/compact", {}))
    raise ValueError(f"unknown tool: {name}")

from __future__ import annotations

import re
from typing import Any

_AGENT_TOOL_NAMES = ("read", "write", "edit", "grep", "shell", "find", "ls")
_TOOL_LINE = re.compile(
    rf"^({'|'.join(_AGENT_TOOL_NAMES)}):\s*(.*)$",
    re.IGNORECASE,
)
_AGENT_TURN = re.compile(r"^agent:\s*", re.IGNORECASE)


def _prune_placeholder(tool: str, payload: str) -> str:
    return f"{tool}: [pruned: {len(payload)} chars]"


def prune_agent_tool_log_text(text: str) -> str:
    """Keep tool lines after the last ``agent:`` turn; prune earlier tool lines."""
    if not text.strip():
        return text
    lines = text.splitlines()
    last_turn = -1
    for i, line in enumerate(lines):
        if _AGENT_TURN.match(line.strip()):
            last_turn = i
    out: list[str] = []
    for i, line in enumerate(lines):
        match = _TOOL_LINE.match(line.strip())
        if match:
            tool, payload = match.group(1).lower(), match.group(2)
            if last_turn < 0 or i > last_turn:
                out.append(line)
            else:
                out.append(_prune_placeholder(tool, payload))
        else:
            out.append(line)
    return "\n".join(out)


def prune_all_agent_tool_lines(text: str) -> str:
    """Replace every agent tool line with a pruned placeholder."""
    if not text.strip():
        return text
    out: list[str] = []
    for line in text.splitlines():
        match = _TOOL_LINE.match(line.strip())
        if match:
            out.append(_prune_placeholder(match.group(1).lower(), match.group(2)))
        else:
            out.append(line)
    return "\n".join(out)


def prune_theater_agent_tool_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Prune ``agent_tool`` theater bodies; keep the latest implement batch verbatim."""
    agent_msgs = [m for m in messages if m.get("message_kind") == "agent_tool"]
    if not agent_msgs:
        return messages
    latest_seq = max(int(m.get("store_seq") or 0) for m in agent_msgs)
    pruned: list[dict[str, Any]] = []
    for msg in messages:
        if msg.get("message_kind") != "agent_tool":
            pruned.append(msg)
            continue
        body = msg.get("body_md")
        if not isinstance(body, str):
            pruned.append(msg)
            continue
        updated = dict(msg)
        seq = int(msg.get("store_seq") or 0)
        if seq < latest_seq:
            updated["body_md"] = prune_all_agent_tool_lines(body)
        else:
            updated["body_md"] = prune_agent_tool_log_text(body)
        pruned.append(updated)
    return pruned


def agent_tool_logs_from_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Extract slice implement agent tool logs for timeline summaries."""
    from agent_core.models import EventType

    logs: list[dict[str, Any]] = []
    for row in events:
        if row.get("event_type") not in {
            EventType.STAGE_STARTED.value,
            EventType.STAGE_PASSED.value,
            EventType.STAGE_FAILED.value,
        }:
            continue
        payload = row.get("payload")
        if not isinstance(payload, dict):
            continue
        stage = str(payload.get("stage_name") or "").strip()
        if stage != "slice.implement":
            continue
        meta = row.get("metadata")
        if not isinstance(meta, dict):
            continue
        raw = meta.get("agent_tool_log")
        if not isinstance(raw, str) or not raw.strip():
            continue
        logs.append(
            {
                "store_seq": int(row.get("store_seq") or 0),
                "slice_id": str(meta.get("slice_id") or ""),
                "log": raw,
            },
        )
    return logs


def agent_tool_timeline_summary(
    events: list[dict[str, Any]],
    *,
    prune: bool = True,
) -> list[dict[str, Any]] | None:
    """Pruned agent tool log excerpts keyed by slice implement stage."""
    logs = agent_tool_logs_from_events(events)
    if not logs:
        return None
    if not prune:
        return [
            {"store_seq": e["store_seq"], "slice_id": e["slice_id"], "log": e["log"]} for e in logs
        ]
    latest_seq = max(e["store_seq"] for e in logs)
    out: list[dict[str, Any]] = []
    for entry in logs:
        text = entry["log"]
        if entry["store_seq"] < latest_seq:
            text = prune_all_agent_tool_lines(text)
        else:
            text = prune_agent_tool_log_text(text)
        out.append(
            {
                "store_seq": entry["store_seq"],
                "slice_id": entry["slice_id"],
                "log": text,
            },
        )
    return out


def projection_prune_agent_tools_enabled() -> bool:
    from nimbusware_env.env_flags import nimbusware_projection_prune_agent_tools_enabled

    return nimbusware_projection_prune_agent_tools_enabled()

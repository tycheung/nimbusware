from __future__ import annotations

from typing import Any


def format_theater_transcript_md(*, run_id: str, messages: list[dict[str, Any]]) -> str:
    lines = ["# Run theater transcript", "", f"**Run ID:** `{run_id}`", ""]
    if not messages:
        lines.append("_No theater messages._")
        return "\n".join(lines) + "\n"
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        actor = str(msg.get("actor_display") or "System")
        headline = str(msg.get("headline") or "")
        severity = str(msg.get("severity") or "info")
        store_seq = int(msg.get("store_seq") or 0)
        event_id = str(msg.get("event_id") or "")
        lines.append(f"## [{store_seq}] {actor} ({severity})")
        lines.append("")
        lines.append(f"**{headline}**")
        if event_id:
            lines.append(f"- event_id: `{event_id}`")
        body = msg.get("body_md")
        if isinstance(body, str) and body.strip():
            lines.append("")
            lines.append(body.strip())
        lines.append("")
    return "\n".join(lines)

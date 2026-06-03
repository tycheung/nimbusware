from __future__ import annotations

import json
from typing import Any

from nimbusware_client.http import stream_collect_text, user_headers


def _parse_sse_chunk(text: str) -> dict[str, dict[str, Any]]:
    events: dict[str, dict[str, Any]] = {}
    event_name = "message"
    data_lines: list[str] = []
    for line in text.splitlines():
        if line.startswith("event:"):
            event_name = line.split(":", 1)[1].strip()
        elif line.startswith("data:"):
            data_lines.append(line.split(":", 1)[1].strip())
        elif not line.strip() and data_lines:
            raw = "\n".join(data_lines)
            try:
                events[event_name] = json.loads(raw)
            except json.JSONDecodeError:
                pass
            data_lines = []
            event_name = "message"
    if data_lines:
        try:
            events[event_name] = json.loads("\n".join(data_lines))
        except json.JSONDecodeError:
            pass
    return events


def fetch_progress_from_stream(
    run_id: str,
    *,
    timeout_seconds: float = 8.0,
) -> dict[str, Any] | None:
    text = stream_collect_text(
        f"/runs/{run_id}/maker-progress/stream",
        params={"poll_seconds": 0.5},
        timeout=timeout_seconds,
        headers=user_headers(),
    )
    parsed = _parse_sse_chunk(text)
    progress = parsed.get("progress")
    return progress if isinstance(progress, dict) else None

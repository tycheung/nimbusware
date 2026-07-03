from __future__ import annotations

from typing import Any

from orchestrator.collab_output_redaction import redact_collab_output

_REDACT_KEYS = ("text", "body", "body_md", "content", "message", "summary")


def redact_turn_dict(turn: dict[str, Any]) -> dict[str, Any]:
    out = dict(turn)
    for key in _REDACT_KEYS:
        val = out.get(key)
        if isinstance(val, str) and val:
            out[key] = redact_collab_output(val)
    return out


def redact_theater_lines(lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [redact_turn_dict(line) for line in lines]

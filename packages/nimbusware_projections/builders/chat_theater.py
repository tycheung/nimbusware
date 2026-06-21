from __future__ import annotations

from typing import Any, Literal

from nimbusware_projections.builders.run_theater import build_run_theater_messages

TheaterProfile = Literal["full", "chat"]

CHAT_THEATER_DEFAULT_CAP = 12
CHAT_THEATER_LIVE_CAP = 96
CHAT_THEATER_SKIP_KINDS = frozenset({"agent_tool"})


def build_chat_theater_digest(
    rows: list[dict[str, Any]],
    *,
    cap: int = CHAT_THEATER_DEFAULT_CAP,
    include_agent_tools: bool = False,
) -> list[dict[str, Any]]:
    messages = build_run_theater_messages(rows)
    if not include_agent_tools:
        messages = [m for m in messages if m.get("message_kind") not in CHAT_THEATER_SKIP_KINDS]
    if cap <= 0:
        return messages
    return messages[-cap:]


def build_theater_messages_for_profile(
    rows: list[dict[str, Any]],
    *,
    profile: TheaterProfile = "full",
    cap: int | None = None,
) -> list[dict[str, Any]]:
    if profile == "chat":
        limit = CHAT_THEATER_DEFAULT_CAP if cap is None else cap
        return build_chat_theater_digest(rows, cap=limit)
    return build_run_theater_messages(rows)

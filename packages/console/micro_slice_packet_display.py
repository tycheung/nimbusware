from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def latest_slice_context_packet_from_timeline(
    timeline: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(timeline, Mapping):
        return None
    events = timeline.get("events")
    if not isinstance(events, list):
        return None
    for row in reversed(events):
        if not isinstance(row, dict):
            continue
        meta = row.get("metadata")
        if not isinstance(meta, dict):
            continue
        packet = meta.get("slice_context_packet")
        if isinstance(packet, dict):
            return packet
    return None

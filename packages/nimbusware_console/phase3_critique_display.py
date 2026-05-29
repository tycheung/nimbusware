"""Timeline readouts for Phase 3 critic stages."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any


def _field(timeline: Mapping[str, Any] | None, key: str) -> dict[str, Any] | None:
    if not isinstance(timeline, Mapping):
        return None
    raw = timeline.get(key)
    return raw if isinstance(raw, dict) else None


def phase3_critique_caption(timeline: Mapping[str, Any] | None) -> str:
    parts: list[str] = []
    for key, label in (
        ("security_critique", "Security"),
        ("performance_critique", "Performance"),
        ("network_resilience_critique", "Network"),
        ("refactor_critique", "Refactor"),
    ):
        block = _field(timeline, key)
        if block is None:
            continue
        verdict = block.get("verdict", "—")
        parts.append(f"{label}={verdict}")
    return "; ".join(parts) if parts else "No Phase 3 critic stages on this timeline."


def phase3_critique_table_rows(timeline: Mapping[str, Any] | None) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for key, label in (
        ("security_critique", "implementation.security_critique"),
        ("performance_critique", "implementation.performance_critique"),
        ("network_resilience_critique", "implementation.network_resilience_critique"),
        ("refactor_critique", "implementation.refactor_critique"),
    ):
        block = _field(timeline, key)
        if block is None:
            continue
        rows.append(
            {
                "Stage": label,
                "Verdict": str(block.get("verdict", "—")),
                "Failing critics": json.dumps(block.get("failing_critics") or []),
            },
        )
    return rows

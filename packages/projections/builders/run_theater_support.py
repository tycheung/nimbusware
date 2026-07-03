from __future__ import annotations

from typing import Any, Literal

from agent_core.mapping import mapping_or_empty

Severity = Literal["info", "warn", "block", "pass"]

SLICE_STAGE_NAMES = frozenset(
    {
        "slice.plan",
        "slice.implement",
        "slice.verify",
        "slice.critique",
        "slice.test",
        "slice.e2e",
        "slice.gate",
    },
)


def stage_name(pl: dict[str, Any]) -> str:
    sn = pl.get("stage_name")
    return str(sn).strip() if isinstance(sn, str) else ""


def row_metadata(row: dict[str, Any]) -> dict[str, Any]:
    return mapping_or_empty(row.get("metadata"))

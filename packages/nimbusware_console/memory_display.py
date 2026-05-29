"""Memory retrieval timeline + run policy display."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from hermes_memory.timeline import (
    memory_indexed_timeline_summary,
    memory_retrieval_timeline_entries,
    memory_retrieval_timeline_summary,
)

__all__ = [
    "memory_indexed_timeline_summary",
    "memory_policy_from_run_summary",
    "memory_policy_table_rows",
    "memory_retrieval_timeline_entries",
    "memory_retrieval_timeline_summary",
]


def memory_policy_from_run_summary(summary: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(summary, Mapping):
        return None
    meta = summary.get("run_created_metadata")
    if not isinstance(meta, dict):
        return None
    mem = meta.get("memory")
    if not isinstance(mem, dict):
        eff = meta.get("memory_effective")
        return dict(eff) if isinstance(eff, dict) else None
    return dict(mem)


def memory_policy_table_rows(policy: Mapping[str, Any] | None) -> list[dict[str, str]]:
    if not isinstance(policy, Mapping):
        return []
    rows: list[dict[str, str]] = []
    for key in (
        "retrieval_enabled",
        "index_contribution",
        "retrieval_k",
        "excerpt_max_chars",
        "embedding_mode",
        "memory_index_version",
    ):
        if key in policy:
            rows.append({"field": key, "value": str(policy[key])})
    return rows


# memory timeline helpers live in ``hermes_memory.timeline`` (re-exported above).

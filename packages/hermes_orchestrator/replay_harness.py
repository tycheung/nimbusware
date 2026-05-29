"""Deterministic replay of event-store rows into read models."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from agent_core.models import serialize_event_persistent, validate_event_dict
from hermes_memory.timeline import (
    memory_indexed_timeline_summary,
    memory_retrieval_timeline_summary,
)
from hermes_orchestrator.read_models import build_run_summary
from hermes_store.protocol import serialized_event_from_row


def events_from_store_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Validate and serialize store rows into persistent event dicts."""
    events: list[dict[str, Any]] = []
    for row in rows:
        payload = serialized_event_from_row(row)
        event = validate_event_dict(payload)
        events.append(serialize_event_persistent(event))
    return events


def build_replay_snapshot(
    rows: list[dict[str, Any]],
    *,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Replay ``list_run_events`` rows into a compact timeline + summary document."""
    rid = run_id
    if rid is None and rows:
        rid = str(rows[0].get("run_id", ""))
    summary = build_run_summary(rows)
    events = events_from_store_rows(rows) if rows else []
    return {
        "run_id": rid or "",
        "summary": summary,
        "event_count": len(events),
        "event_types": [ev.get("event_type") for ev in events],
        "memory_retrieval": memory_retrieval_timeline_summary(events),
        "memory_indexed": memory_indexed_timeline_summary(events),
    }


def replay_snapshot_for_hash(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Drop volatile fields so golden hashes stay stable across replays."""
    summary = snapshot.get("summary")
    summary_out: dict[str, Any] | None = None
    if isinstance(summary, dict):
        summary_out = {
            k: v
            for k, v in summary.items()
            if k not in {"run_created_metadata"}
        }
    memory_indexed = snapshot.get("memory_indexed")
    memory_indexed_out = None
    if isinstance(memory_indexed, dict):
        memory_indexed_out = {
            k: v for k, v in memory_indexed.items() if k != "generation_id"
        }
    return {
        "run_id": snapshot.get("run_id"),
        "summary": summary_out,
        "event_count": snapshot.get("event_count"),
        "event_types": snapshot.get("event_types"),
        "memory_retrieval": snapshot.get("memory_retrieval"),
        "memory_indexed": memory_indexed_out,
    }


def stable_replay_hash(snapshot: dict[str, Any]) -> str:
    """SHA-256 of canonical JSON for regression comparisons."""
    normalized = replay_snapshot_for_hash(snapshot)
    payload = json.dumps(normalized, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def diff_replay_snapshots(
    left: dict[str, Any],
    right: dict[str, Any],
    *,
    left_label: str = "left",
    right_label: str = "right",
) -> list[str]:
    """Human-readable top-level diff lines between two replay snapshots."""
    lines: list[str] = []
    keys = sorted(set(left.keys()) | set(right.keys()))
    for key in keys:
        lv = left.get(key)
        rv = right.get(key)
        if lv == rv:
            continue
        lines.append(f"{key}: {left_label}={lv!r} {right_label}={rv!r}")
    return lines


def load_fixture_rows(path: Path) -> tuple[str | None, list[dict[str, Any]]]:
    """Load anonymized event rows from ``tests/fixtures/memory/*.json``."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        return None, raw
    if not isinstance(raw, dict):
        msg = f"fixture must be object or list, got {type(raw).__name__}"
        raise ValueError(msg)
    rows = raw.get("rows")
    if not isinstance(rows, list):
        msg = "fixture object must include a rows list"
        raise ValueError(msg)
    run_id = raw.get("run_id")
    return (str(run_id) if run_id else None, rows)


def load_run_rows_from_store(store: Any, run_id: str) -> list[dict[str, Any]]:
    """Fetch ordered event rows for a run from any event store exposing ``list_run_events``."""
    rows = store.list_run_events(run_id)
    if not isinstance(rows, list):
        msg = "list_run_events must return a list"
        raise TypeError(msg)
    return rows

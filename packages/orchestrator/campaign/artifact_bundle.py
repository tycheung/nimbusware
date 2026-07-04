from __future__ import annotations

import hashlib
import json
from typing import Any
from uuid import UUID

from agent_core.mapping import mapping_or_empty
from agent_core.models import EventType
from orchestrator.role_context_audit import (
    IMPLEMENT_FORBIDDEN_CONTEXT,
    filter_implement_context,
    implement_context_sources,
)
from orchestrator.slice.handoff import latest_handoff_from_events


def _payload(row: dict[str, Any]) -> dict[str, Any]:
    return mapping_or_empty(row.get("payload"))


def _metadata(row: dict[str, Any]) -> dict[str, Any]:
    return mapping_or_empty(row.get("metadata"))


def _latest_slice_plan_packet(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    latest: dict[str, Any] | None = None
    latest_seq = -1
    for row in events:
        if row.get("event_type") not in {
            EventType.STAGE_PASSED.value,
            EventType.STAGE_FAILED.value,
        }:
            continue
        if _payload(row).get("stage_name") != "slice.gate":
            continue
        packet = _metadata(row).get("slice_context_packet")
        if not isinstance(packet, dict):
            continue
        seq = int(row.get("store_seq") or 0)
        if seq >= latest_seq:
            latest_seq = seq
            latest = packet
    return latest


def _memory_index_hits(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for row in reversed(events):
        meta = _metadata(row)
        raw = meta.get("memory_retrieval_hits")
        if isinstance(raw, list) and raw:
            hits = [h for h in raw if isinstance(h, dict)]
            break
    return hits


def _operator_steer_messages(events: list[dict[str, Any]]) -> list[str]:
    out: list[str] = []
    for row in events:
        meta = _metadata(row)
        interjection = meta.get("interjection")
        if not isinstance(interjection, dict):
            continue
        msg = str(interjection.get("message") or "").strip()
        if msg:
            out.append(msg[:500])
    return out[-20:]


def _failure_learnings(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in events:
        if row.get("event_type") != EventType.FINDING_CREATED.value:
            continue
        payload = _payload(row)
        rows.append(
            {
                "finding_id": str(row.get("event_id") or ""),
                "category": payload.get("category"),
                "severity": payload.get("severity"),
                "summary": str(payload.get("summary") or payload.get("title") or "")[:500],
            },
        )
    return rows[-30:]


def build_campaign_artifact_bundle(
    events: list[dict[str, Any]],
    *,
    run_id: UUID | str,
) -> dict[str, Any]:
    """Export implement-safe context sources without chat transcript or theater dumps."""
    handoff = latest_handoff_from_events(events)
    sources: dict[str, Any] = {
        "slice.plan": _latest_slice_plan_packet(events),
        "slice.handoff": handoff.model_dump(mode="json") if handoff is not None else None,
        "memory.index": _memory_index_hits(events),
        "operator.steer": _operator_steer_messages(events),
        "failure.learning": _failure_learnings(events),
    }
    filtered = filter_implement_context(sources)
    payload = {
        "version": 1,
        "run_id": str(run_id),
        "allowed_sources": sorted(implement_context_sources()),
        "forbidden_omitted": sorted(IMPLEMENT_FORBIDDEN_CONTEXT),
        "sources": filtered,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    payload["checksum_sha256"] = hashlib.sha256(raw).hexdigest()
    return payload

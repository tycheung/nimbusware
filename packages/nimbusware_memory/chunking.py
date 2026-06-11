from __future__ import annotations

from typing import Any
from uuid import UUID

from agent_core.models import EventType, Verdict
from nimbusware_memory.models import MemoryChunkDraft
from nimbusware_store.protocol import serialized_event_from_row

_MAX_EXCERPT_CHARS = 2000


def run_index_contribution_enabled(metadata: object) -> bool:
    """Default True unless ``metadata.memory.index_contribution`` is explicitly false."""
    if not isinstance(metadata, dict):
        return True
    mem = metadata.get("memory")
    if not isinstance(mem, dict):
        return True
    raw = mem.get("index_contribution")
    if raw is None:
        return True
    if isinstance(raw, bool):
        return raw
    return str(raw).strip().lower() not in ("0", "false", "no")


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)] + "..."


def _finding_excerpt(payload: dict[str, Any]) -> str:
    parts: list[str] = []
    cat = payload.get("category")
    if cat:
        parts.append(f"category={cat}")
    sev = payload.get("severity")
    if sev:
        parts.append(f"severity={sev}")
    src = payload.get("source_artifact")
    if src:
        parts.append(f"source={src}")
    repro = payload.get("repro_steps")
    if isinstance(repro, list):
        parts.append("repro:\n" + "\n".join(str(x) for x in repro[:12]))
    fixes = payload.get("required_fixes")
    if isinstance(fixes, list) and fixes:
        parts.append(f"required_fixes_count={len(fixes)}")
    return _truncate("\n".join(parts), _MAX_EXCERPT_CHARS)


def _gate_fail_excerpt(payload: dict[str, Any]) -> str:
    stage = payload.get("stage_name", "")
    verdict = payload.get("verdict", "")
    failing = payload.get("failing_critics") or []
    return _truncate(
        f"gate stage={stage} verdict={verdict} failing_critics={len(failing)}",
        _MAX_EXCERPT_CHARS,
    )


def chunks_from_event_rows(rows: list[dict[str, Any]]) -> list[MemoryChunkDraft]:
    """Scan ordered event rows and emit chunk drafts for memory indexing."""
    skip_run_index: dict[UUID, bool] = {}
    for row in rows:
        if row.get("event_type") != EventType.RUN_CREATED.value:
            continue
        rid = UUID(str(row["run_id"]))
        meta = row.get("metadata") or {}
        skip_run_index[rid] = not run_index_contribution_enabled(meta)

    out: list[MemoryChunkDraft] = []
    for row in rows:
        et = str(row.get("event_type", ""))
        rid = UUID(str(row["run_id"]))
        if skip_run_index.get(rid):
            continue
        store_seq = int(row["store_seq"]) if row.get("store_seq") is not None else None
        pl = row.get("payload") or {}
        if not isinstance(pl, dict):
            pl = serialized_event_from_row(row).get("payload") or {}
            if not isinstance(pl, dict):
                continue

        if et == EventType.FINDING_CREATED.value:
            finding_id_raw = pl.get("finding_id")
            finding_id = UUID(str(finding_id_raw)) if finding_id_raw else None
            out.append(
                MemoryChunkDraft(
                    run_id=rid,
                    source_event_type=et,
                    source_store_seq=store_seq,
                    finding_id=finding_id,
                    category=str(pl.get("category") or "") or None,
                    severity=str(pl.get("severity") or "") or None,
                    excerpt=_finding_excerpt(pl),
                ),
            )
            continue

        if et == EventType.GATE_DECISION_EMITTED.value:
            if str(pl.get("verdict", "")).upper() != Verdict.FAIL.value:
                continue
            out.append(
                MemoryChunkDraft(
                    run_id=rid,
                    source_event_type=et,
                    source_store_seq=store_seq,
                    finding_id=None,
                    category="gate",
                    severity=None,
                    excerpt=_gate_fail_excerpt(pl),
                ),
            )
    return out

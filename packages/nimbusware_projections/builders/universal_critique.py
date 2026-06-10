from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from agent_core.mapping import mapping_or_empty
from agent_core.models import EventType
from agent_core.timeline_metadata import critique_coverage_from_run_created_metadata
from nimbusware_orchestrator.critique_routing import CRITIQUE_STAGE_TO_PRODUCER

_CRITIQUE_STAGE_ORDER: tuple[str, ...] = (
    "planner.critique",
    "implementation.critique",
    "test_writer.critique",
    "frontend_writer.critique",
    "module_integrator.critique",
    "agent_evaluator.critique",
    "self_refinement.critique",
)


def _critique_row_from_gate_event(ev: dict[str, Any]) -> dict[str, Any] | None:
    payload = ev.get("payload")
    pl = mapping_or_empty(payload)
    sn = pl.get("stage_name")
    if not isinstance(sn, str) or not sn.endswith(".critique"):
        return None
    meta = ev.get("metadata")
    meta_d = mapping_or_empty(meta)
    if meta_d.get("integrator_gate") is True:
        return None
    row = {
        "event_id": ev.get("event_id"),
        "occurred_at": ev.get("occurred_at"),
        "stage_name": sn,
        "verdict": pl.get("verdict"),
        "failure_reason_code": pl.get("failure_reason_code"),
    }
    failing = pl.get("failing_critics")
    if isinstance(failing, list) and failing:
        row["failing_critics"] = [str(x) for x in failing]
    producer = CRITIQUE_STAGE_TO_PRODUCER.get(sn)
    if producer is not None:
        row["producer_taxonomy_key"] = producer
    return row


def universal_critique_timeline_entries(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Latest ``gate.decision.emitted`` per universal-critique stage (chronological scan)."""
    want = EventType.GATE_DECISION_EMITTED.value
    by_stage: dict[str, dict[str, Any]] = {}
    for ev in events:
        if ev.get("event_type") != want:
            continue
        row = _critique_row_from_gate_event(ev)
        if row is None:
            continue
        sn = row["stage_name"]
        if isinstance(sn, str):
            by_stage[sn] = row
    ordered: list[dict[str, Any]] = []
    for name in _CRITIQUE_STAGE_ORDER:
        if name in by_stage:
            ordered.append(by_stage[name])
    for name in sorted(by_stage.keys()):
        if name not in _CRITIQUE_STAGE_ORDER:
            ordered.append(by_stage[name])
    return ordered


def universal_critique_effective_from_run_created_metadata(
    metadata: Mapping[str, Any] | dict[str, Any],
) -> dict[str, Any] | None:
    if not isinstance(metadata, Mapping):
        return None
    raw = metadata.get("universal_critique_effective")
    return dict(raw) if isinstance(raw, dict) else None


def universal_critique_timeline_summary(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Rollup of latest universal-critique gate decisions on the run."""
    stages = universal_critique_timeline_entries(events)
    if not stages:
        return None
    out: dict[str, Any] = {
        "stages": stages,
        "stage_count": len(stages),
        "fail_count": 0,
        "pass_count": 0,
        "distinct_fail_stages": [],
    }
    fail_count = 0
    pass_count = 0
    fail_stage_names: list[str] = []
    for s in stages:
        v = s.get("verdict")
        verdict = str(v).strip().upper() if v is not None else ""
        if verdict == "FAIL":
            fail_count += 1
            stage_name = s.get("stage_name")
            if isinstance(stage_name, str) and stage_name.strip():
                fail_stage_names.append(stage_name.strip())
        elif verdict == "PASS":
            pass_count += 1
    out["fail_count"] = fail_count
    out["pass_count"] = pass_count
    stage_count = len(stages)
    if stage_count > 0:
        out["fail_rate"] = round(fail_count / stage_count, 4)
    out["distinct_fail_stages"] = sorted(set(fail_stage_names))
    critique_coverage: dict[str, Any] | None = None
    for ev in events:
        if ev.get("event_type") != EventType.RUN_CREATED.value:
            continue
        meta = ev.get("metadata")
        if isinstance(meta, dict):
            critique_coverage = critique_coverage_from_run_created_metadata(meta)
        break
    if critique_coverage is not None:
        out["critique_coverage"] = critique_coverage
    for ev in events:
        if ev.get("event_type") != EventType.RUN_CREATED.value:
            continue
        meta = ev.get("metadata")
        if isinstance(meta, dict):
            uce = universal_critique_effective_from_run_created_metadata(meta)
            if uce is not None:
                if isinstance(uce.get("unanimous_gate_enforce"), bool):
                    out["unanimous_gate_effective"] = uce["unanimous_gate_enforce"]
                if isinstance(uce.get("default_enabled"), bool):
                    out["default_enabled_effective"] = uce["default_enabled"]
                if isinstance(uce.get("production_default_on"), bool):
                    out["production_default_on"] = uce["production_default_on"]
        break
    return out


__all__ = [
    "universal_critique_effective_from_run_created_metadata",
    "universal_critique_timeline_entries",
    "universal_critique_timeline_summary",
]

from __future__ import annotations

from typing import Any

from agent_core.models import EventType
from hermes_orchestrator.critic_matrix_live import (
    build_live_critic_matrix_rows,
    critic_matrix_unanimous_summary,
)
from hermes_orchestrator.llm.common import (
    IMPLEMENTATION_CRITIQUE_STAGE,
    TEST_WRITER_CRITIQUE_STAGE,
)
from hermes_orchestrator.stage_graph import stage_graph_timeline_summary_from_metadata

_WRITER_GATE_STAGE: dict[str, str] = {
    "implementation": IMPLEMENTATION_CRITIQUE_STAGE,
    "test_writer": TEST_WRITER_CRITIQUE_STAGE,
    "frontend_writer": "frontend_writer.critique",
}


def stage_graph_timeline_summary(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Compact stage DAG rollup from frozen ``run.created`` ``metadata.stage_graph``."""
    for ev in events:
        if ev.get("event_type") != EventType.RUN_CREATED.value:
            continue
        meta = ev.get("metadata")
        if isinstance(meta, dict):
            return stage_graph_timeline_summary_from_metadata(meta)
        break
    return None


def parallel_writer_groups_timeline_summary(
    events: list[dict[str, Any]],
) -> list[dict[str, Any]] | None:
    """Roll up parallel writer groups with gate pass/fail per mapped critique stage."""
    stage_graph_meta: dict[str, Any] | None = None
    for ev in events:
        if ev.get("event_type") != EventType.RUN_CREATED.value:
            continue
        meta = ev.get("metadata")
        if isinstance(meta, dict):
            sg = meta.get("stage_graph")
            stage_graph_meta = sg if isinstance(sg, dict) else None
        break
    if not stage_graph_meta:
        return None
    parallel_groups = stage_graph_meta.get("parallel_groups")
    if not isinstance(parallel_groups, dict) or not parallel_groups:
        return None
    gate_verdict: dict[str, str] = {}
    for ev in events:
        if ev.get("event_type") != EventType.GATE_DECISION_EMITTED.value:
            continue
        pl = ev.get("payload")
        if not isinstance(pl, dict):
            continue
        sn = pl.get("stage_name")
        if isinstance(sn, str) and sn.strip():
            verdict_raw = pl.get("verdict")
            gate_verdict[sn.strip()] = (
                str(verdict_raw).strip().upper() if verdict_raw is not None else ""
            )

    stage_started: dict[str, dict[str, Any]] = {}
    stage_passed: dict[str, dict[str, Any]] = {}
    stage_failed: dict[str, dict[str, Any]] = {}
    dispatch_mode = "sequential"
    for ev in events:
        et = ev.get("event_type")
        pl = ev.get("payload")
        if not isinstance(pl, dict):
            continue
        sn_raw = pl.get("stage_name")
        if not isinstance(sn_raw, str):
            continue
        sn = sn_raw.strip()
        stage_meta_raw = ev.get("metadata")
        stage_meta: dict[str, Any] = stage_meta_raw if isinstance(stage_meta_raw, dict) else {}
        if et == EventType.STAGE_STARTED.value and sn in (
            "implementation",
            "test_writer",
            "frontend_writer",
        ):
            stage_started[sn] = {
                "occurred_at": ev.get("occurred_at"),
                "dispatch_mode": stage_meta.get("dispatch_mode"),
                "body_mode": stage_meta.get("body_mode"),
            }
            dm = stage_meta.get("dispatch_mode")
            if isinstance(dm, str) and dm.strip():
                dispatch_mode = dm.strip().lower()
        elif et == EventType.STAGE_PASSED.value and sn in (
            "implementation",
            "test_writer",
            "frontend_writer",
        ):
            stage_passed[sn] = {
                "duration_ms": pl.get("duration_ms"),
                "occurred_at": ev.get("occurred_at"),
                "exit_code": stage_meta.get("exit_code"),
                "body_mode": stage_meta.get("body_mode"),
            }
        elif et == EventType.STAGE_FAILED.value and sn in (
            "implementation",
            "test_writer",
            "frontend_writer",
        ):
            stage_failed[sn] = {
                "occurred_at": ev.get("occurred_at"),
                "failure_reason": stage_meta.get("failure_reason") or pl.get("reason_code"),
                "exit_code": stage_meta.get("exit_code"),
                "body_mode": stage_meta.get("body_mode"),
            }

    out: list[dict[str, Any]] = []
    for group_id, stages in parallel_groups.items():
        if not isinstance(stages, list):
            continue
        gate_pass: list[str] = []
        gate_fail: list[str] = []
        stage_details: list[dict[str, Any]] = []
        for stage in stages:
            stage_key = str(stage)
            critique_stage = _WRITER_GATE_STAGE.get(stage_key, stage_key)
            verdict = gate_verdict.get(critique_stage, "")
            if verdict == "PASS":
                gate_pass.append(stage_key)
            elif verdict == "FAIL":
                gate_fail.append(stage_key)
            detail: dict[str, Any] = {"stage_name": stage_key}
            if stage_key in stage_started:
                detail["started_at"] = stage_started[stage_key].get("occurred_at")
                if stage_started[stage_key].get("body_mode") is not None:
                    detail["body_mode"] = stage_started[stage_key].get("body_mode")
            if stage_key in stage_passed:
                detail["passed"] = True
                detail["duration_ms"] = stage_passed[stage_key].get("duration_ms")
                if stage_passed[stage_key].get("exit_code") is not None:
                    detail["exit_code"] = stage_passed[stage_key].get("exit_code")
                if stage_passed[stage_key].get("body_mode") is not None:
                    detail["body_mode"] = stage_passed[stage_key].get("body_mode")
            elif stage_key in stage_failed:
                detail["passed"] = False
                if stage_failed[stage_key].get("exit_code") is not None:
                    detail["exit_code"] = stage_failed[stage_key].get("exit_code")
                if stage_failed[stage_key].get("failure_reason") is not None:
                    detail["failure_reason"] = stage_failed[stage_key].get("failure_reason")
                if stage_failed[stage_key].get("body_mode") is not None:
                    detail["body_mode"] = stage_failed[stage_key].get("body_mode")
            else:
                detail["passed"] = stage_key in stage_passed
            stage_details.append(detail)
        out.append(
            {
                "group_id": str(group_id),
                "stages": [str(s) for s in stages],
                "dispatch_mode": dispatch_mode,
                "stage_details": stage_details,
                "gate_pass": gate_pass,
                "gate_fail": gate_fail,
            },
        )
    return out or None


def critic_matrix_live_timeline_summary(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Live orchestration critic matrix (gate decisions + pending critique stages)."""
    rows = build_live_critic_matrix_rows(events)
    if not rows:
        return None
    summary = critic_matrix_unanimous_summary(rows)
    return {"rows": rows, "summary": summary}


__all__ = [
    "critic_matrix_live_timeline_summary",
    "parallel_writer_groups_timeline_summary",
    "stage_graph_timeline_summary",
]

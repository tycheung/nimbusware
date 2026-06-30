from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import HTTPException, Response
from fastapi.routing import APIRouter

from agent_core.models import serialize_event_persistent, validate_event_dict
from nimbusware_api.deps import StoreDep
from nimbusware_api.errors import problem
from nimbusware_api.preflight_read_model import preflight_timeline_summary
from nimbusware_api.schemas.openapi import (
    PROBLEM_RESPONSE_404,
    PROBLEM_RESPONSE_422,
    PROBLEM_RESPONSE_500,
    RUN_DETAIL_LINK_HEADER,
    RUN_FINDINGS_LINK_HEADER,
    RUN_TIMELINE_RESPONSE_200,
    format_run_detail_link_header,
    format_run_findings_link_header,
    format_run_timeline_link_header,
)
from nimbusware_api.schemas.runs import RunDetailResponse, RunTimelineResponse
from nimbusware_console.critic_reliability_display import (
    critic_reliability_caption,
    critic_reliability_summary_from_events,
    critic_reliability_table_rows,
)
from nimbusware_maker.memory_influence_display import format_retrieval_rows
from nimbusware_memory.timeline import (
    memory_indexed_timeline_summary,
    memory_retrieval_timeline_entries,
    memory_retrieval_timeline_summary,
)
from nimbusware_projections.builders import (
    agent_evaluator_timeline_summary,
    critic_matrix_live_timeline_summary,
    gate_overridden_timeline_history,
    gate_overridden_timeline_summary,
    integrator_gate_timeline_delta,
    integrator_gate_timeline_history,
    parallel_writer_groups_timeline_summary,
    persona_assignment_timeline_summary,
    run_escalated_timeline_delta,
    run_escalated_timeline_history,
    scraper_fetch_timeline_summary,
    security_scan_on_verify_timeline_history,
    self_refinement_marker_timeline_history,
    self_refinement_timeline_summary,
    stage_graph_timeline_summary,
    universal_critique_timeline_summary,
)
from nimbusware_projections.run_summary import build_run_summary
from nimbusware_store.protocol import serialized_event_from_row

router = APIRouter()


@router.get(
    "/runs/{run_id}",
    response_model=RunDetailResponse,
    response_model_exclude_none=True,
    responses={
        200: {
            "description": "Run summary from replayed events",
            "headers": {
                "Link": RUN_DETAIL_LINK_HEADER,
            },
            "content": {
                "application/json": {
                    "example": {
                        "status": "running",
                        "workflow_profile": "default",
                        "event_count": 5,
                        "findings_count": 0,
                        "has_escalation": False,
                    },
                },
            },
        },
        404: PROBLEM_RESPONSE_404,
        422: PROBLEM_RESPONSE_422,
        500: PROBLEM_RESPONSE_500,
    },
)
def get_run(run_id: UUID, store: StoreDep, response: Response) -> RunDetailResponse:
    rows = store.list_run_events(str(run_id))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(run_id)}),
        )
    summary = build_run_summary(rows)
    rid = str(run_id)
    response.headers["Link"] = format_run_detail_link_header(rid)
    return RunDetailResponse.model_validate({**summary, "run_id": rid})


@router.get(
    "/runs/{run_id}/timeline",
    response_model=RunTimelineResponse,
    responses={
        200: RUN_TIMELINE_RESPONSE_200,
        404: PROBLEM_RESPONSE_404,
        422: PROBLEM_RESPONSE_422,
        500: PROBLEM_RESPONSE_500,
    },
)
def timeline(run_id: UUID, store: StoreDep, response: Response) -> RunTimelineResponse:
    rows = store.list_run_events(str(run_id))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(run_id)}),
        )
    rid = str(run_id)
    response.headers["Link"] = format_run_timeline_link_header(rid)
    events: list[dict[str, Any]] = []
    for r in rows:
        d = serialized_event_from_row(r)
        parsed = validate_event_dict(d)
        persisted = serialize_event_persistent(parsed)
        persisted["store_seq"] = int(r.get("store_seq") or 0)
        events.append(persisted)
    ig_hist = integrator_gate_timeline_history(events)
    ig_sum = ig_hist[-1] if ig_hist else None
    ig_delta = integrator_gate_timeline_delta(events)
    re_hist = run_escalated_timeline_history(events)
    re_sum = re_hist[-1] if re_hist else None
    re_delta = run_escalated_timeline_delta(events)
    go_hist = gate_overridden_timeline_history(events)
    go_sum = gate_overridden_timeline_summary(events)
    ss_hist = security_scan_on_verify_timeline_history(events)
    ss_sum = ss_hist[-1] if ss_hist else None
    sr_markers = self_refinement_marker_timeline_history(events)
    from nimbusware_orchestrator.micro_slice import micro_slice_timeline_summary
    from nimbusware_orchestrator.refactor_stage import refactor_critique_timeline_summary
    from nimbusware_orchestrator.scan_critique_handlers import (
        network_resilience_critique_timeline_summary,
        performance_critique_timeline_summary,
        security_critique_timeline_summary,
    )

    custom_agent_summary: dict[str, Any] | None = None
    for event_row in events:
        if event_row.get("event_type") == "run.created":
            meta = event_row.get("metadata")
            if isinstance(meta, dict) and isinstance(meta.get("custom_agent"), dict):
                custom_agent_summary = meta["custom_agent"]
            break
    return RunTimelineResponse(
        run_id=rid,
        events=events,
        integrator_gate=ig_sum,
        integrator_gate_history=ig_hist or None,
        integrator_gate_delta=ig_delta,
        agent_evaluator=agent_evaluator_timeline_summary(events),
        self_refinement=self_refinement_timeline_summary(events),
        self_refinement_marker_history=sr_markers or None,
        run_escalated=re_sum,
        run_escalated_history=re_hist or None,
        run_escalated_delta=re_delta,
        gate_overridden=go_sum,
        gate_overridden_history=go_hist or None,
        security_scan_on_verify=ss_sum,
        security_scan_on_verify_history=ss_hist or None,
        preflight=preflight_timeline_summary(events),
        scraper_fetch=scraper_fetch_timeline_summary(events),
        universal_critique=universal_critique_timeline_summary(events),
        stage_graph=stage_graph_timeline_summary(events),
        parallel_writer_groups=parallel_writer_groups_timeline_summary(events),
        critic_matrix_live=critic_matrix_live_timeline_summary(events),
        persona_assignment=persona_assignment_timeline_summary(events),
        micro_slice=micro_slice_timeline_summary(events),
        custom_agent=custom_agent_summary,
        security_critique=security_critique_timeline_summary(events),
        performance_critique=performance_critique_timeline_summary(events),
        network_resilience_critique=network_resilience_critique_timeline_summary(events),
        refactor_critique=refactor_critique_timeline_summary(events),
        memory_retrieval=memory_retrieval_timeline_summary(events),
        memory_indexed=memory_indexed_timeline_summary(events),
    )


@router.get(
    "/runs/{run_id}/findings",
    responses={
        200: {
            "description": "Finding events for the run",
            "headers": {
                "Link": RUN_FINDINGS_LINK_HEADER,
            },
            "content": {
                "application/json": {
                    "example": {
                        "run_id": "11111111-1111-4111-8111-111111111111",
                        "findings": [],
                    },
                },
            },
        },
        404: PROBLEM_RESPONSE_404,
        422: PROBLEM_RESPONSE_422,
        500: PROBLEM_RESPONSE_500,
    },
)
def findings(run_id: UUID, store: StoreDep, response: Response) -> dict[str, Any]:
    rows = store.list_run_events(str(run_id))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(run_id)}),
        )
    rid = str(run_id)
    response.headers["Link"] = format_run_findings_link_header(rid)
    out: list[dict[str, Any]] = []
    for r in rows:
        if r["event_type"] != "finding.created":
            continue
        d = serialized_event_from_row(r)
        ev = validate_event_dict(d)
        out.append(serialize_event_persistent(ev))
    return {"run_id": rid, "findings": out}


@router.get(
    "/runs/{run_id}/critic-reliability",
    responses={404: PROBLEM_RESPONSE_404},
)
def critic_reliability(run_id: UUID, store: StoreDep) -> dict[str, Any]:
    rows = store.list_run_events(str(run_id))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(run_id)}),
        )
    summary = critic_reliability_summary_from_events(rows)
    return {
        "run_id": str(run_id),
        "caption": critic_reliability_caption(summary),
        "rows": critic_reliability_table_rows(summary),
        "summary": summary,
    }


@router.get(
    "/runs/{run_id}/memory-influence",
    responses={
        200: {
            "description": "Memory retrieval rows for Maker progress panel",
            "content": {
                "application/json": {
                    "example": {
                        "run_id": "11111111-1111-4111-8111-111111111111",
                        "rows": [],
                        "summary": None,
                    },
                },
            },
        },
        404: PROBLEM_RESPONSE_404,
        422: PROBLEM_RESPONSE_422,
        500: PROBLEM_RESPONSE_500,
    },
)
def memory_influence(run_id: UUID, store: StoreDep) -> dict[str, Any]:
    rows = store.list_run_events(str(run_id))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(run_id)}),
        )
    events = [serialized_event_from_row(r) for r in rows]
    raw = memory_retrieval_timeline_entries(events)
    return {
        "run_id": str(run_id),
        "rows": format_retrieval_rows(raw),
        "summary": memory_retrieval_timeline_summary(events),
    }

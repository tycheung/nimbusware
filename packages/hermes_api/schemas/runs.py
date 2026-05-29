"""Typed JSON shapes for run list/detail (plan §6.2, PLAN_GAP backlog #3)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class RunSummary(BaseModel):
    """Shape returned by ``build_run_summary`` (replay of ``list_run_events``)."""

    model_config = ConfigDict(extra="forbid")

    status: str
    workflow_profile: str | None
    event_count: int
    latest_event_type: str
    terminal_event_type: str | None = None
    findings_count: int
    has_escalation: bool
    run_created_metadata: dict[str, Any] = Field(default_factory=dict)
    persona_assignment: dict[str, Any] | None = None


class RunDetailResponse(RunSummary):
    """``GET /v1/runs/{run_id}`` — summary plus identifier."""

    run_id: str


class RunTimelineResponse(BaseModel):
    """``GET /v1/runs/{run_id}/timeline`` — replayed events plus read-model summaries."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    events: list[dict[str, Any]]
    integrator_gate: dict[str, Any] | None = None
    integrator_gate_history: list[dict[str, Any]] | None = None
    integrator_gate_delta: dict[str, Any] | None = None
    agent_evaluator: dict[str, Any] | None = None
    self_refinement: dict[str, Any] | None = None
    self_refinement_marker_history: list[dict[str, Any]] | None = None
    run_escalated: dict[str, Any] | None = None
    run_escalated_history: list[dict[str, Any]] | None = None
    run_escalated_delta: dict[str, Any] | None = None
    security_scan_on_verify: dict[str, Any] | None = None
    security_scan_on_verify_history: list[dict[str, Any]] | None = None
    preflight: dict[str, Any] | None = None
    scraper_fetch: dict[str, Any] | None = None
    universal_critique: dict[str, Any] | None = None
    stage_graph: dict[str, Any] | None = None
    parallel_writer_groups: list[dict[str, Any]] | None = None
    critic_matrix_live: dict[str, Any] | None = None
    persona_assignment: dict[str, Any] | None = None
    micro_slice: dict[str, Any] | None = None
    custom_agent: dict[str, Any] | None = None


class RunListResponse(BaseModel):
    """``GET /v1/runs`` paginated list."""

    model_config = ConfigDict(extra="forbid")

    run_ids: list[str]
    total: int
    has_more: bool
    limit: int
    offset: int
    order: Literal["newest_first", "oldest_first"]
    include_summary: int = Field(ge=0, le=1)
    workflow_profile: str | None = None
    workflow_profile_prefix: str | None = None
    created_after: str | None = None
    created_before: str | None = None
    has_escalation: int | None = Field(default=None, ge=0, le=1)
    summaries: dict[str, RunSummary] | None = None
    next_cursor: str | None = None
    status: str | None = None

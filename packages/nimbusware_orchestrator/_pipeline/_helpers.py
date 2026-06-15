from __future__ import annotations

import asyncio
import hashlib
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse
from uuid import UUID, uuid4

import httpx

from agent_core.mapping import mapping_or_empty
from agent_core.models import (
    EventType,
    FindingCreatedEvent,
    FindingCreatedPayload,
    FindingFixStrictnessSettings,
    GateDecisionEmittedEvent,
    GateDecisionEmittedPayload,
    ModelPreflightPassedEvent,
    ModelPreflightPassedPayload,
    ModelPreflightStartedEvent,
    ModelPreflightStartedPayload,
    ModelSelectedFallbackEvent,
    ModelSelectedFallbackPayload,
    ModelSelectedPrimaryEvent,
    ModelSelectedPrimaryPayload,
    RunCreatedEvent,
    RunCreatedPayload,
    RunStartedEvent,
    RunStartedPayload,
    SelfRefinementLoopSignalledEvent,
    SelfRefinementLoopSignalledPayload,
    Severity,
    StageFailedEvent,
    StageFailedPayload,
    StagePassedEvent,
    StagePassedPayload,
    StageStartedEvent,
    StageStartedPayload,
    Verdict,
    validate_event_dict,
)
from nimbusware_env.env_flags import (
    env_str,
    env_tri_state,
    env_truthy,
    nimbusware_outbound_fetch_enabled,
    nimbusware_use_llm_enabled,
)
from nimbusware_executor.fetch import EgressResponseTooLarge
from nimbusware_extensions import SelfRefinementPolicy, load_self_refinement_policy
from nimbusware_extensions.phase2 import AgentEvaluator, agent_evaluator_score_band
from nimbusware_extensions.self_refinement import SelfRefinementEvaluator
from nimbusware_orchestrator.anti_deadlock import (
    load_anti_deadlock_settings,
    should_emit_anti_deadlock_escalation,
)
from nimbusware_orchestrator.critique_routing import (
    assert_critique_coverage_complete,
    critique_coverage_snapshot,
    load_critique_router,
    taxonomy_keys_for_run_lifecycle,
)
from nimbusware_orchestrator.escalation_execution import append_run_escalated
from nimbusware_orchestrator.escalation_threshold import (
    load_auto_escalate_after_cumulative_findings,
    load_escalate_after_cumulative_gate_failures,
    load_escalate_after_cumulative_high_severity_findings,
    load_escalate_after_cumulative_stage_failures,
    load_notice_escalate_at_cumulative_findings,
)
from nimbusware_orchestrator.fast_slice_critique import (
    fast_slice_env_effective,
    fast_slice_skips_optional_critique_matrix,
    max_open_finding_severity,
)
from nimbusware_orchestrator.frontend_writer_stage import run_frontend_writer_stage
from nimbusware_orchestrator.ingress import (
    assert_agent_evaluator_persona_in_shelves,
    assert_bundle_catalog_maps_resolve,
    assert_known_workflow,
    assert_persona_shelves_valid,
    assert_stage_graph_valid,
    assert_taxonomy_keys_resolve,
)
from nimbusware_orchestrator.integration_adapter_writer_stage import (
    emit_live_integration_adapter_writer_stage,
    emit_stub_integration_adapter_writer_stage,
    integration_adapter_writer_stage_would_emit,
)
from nimbusware_orchestrator.integrator_gate import (
    effective_integrator_min_score_to_pass,
    integrator_gate_workflow_enabled,
    load_bundle_tags_for_bundle_id,
    load_bundle_title_for_bundle_id,
    load_integrator_gate_emit_enabled,
    parse_integrator_gate_project_tags,
    rank_bundle_compatibility_candidates,
    select_bundle_id_for_workflow,
    workflow_profile_from_run_created_rows,
)
from nimbusware_orchestrator.llm.common import (
    FRONTEND_WRITER_CRITIQUE_STAGE,
    IMPLEMENTATION_CRITIQUE_STAGE,
    MODULE_INTEGRATOR_CRITIQUE_STAGE,
    PLANNER_CRITIQUE_STAGE,
    TEST_WRITER_CRITIQUE_STAGE,
)
from nimbusware_orchestrator.llm_plan import (
    emit_stub_frontend_writer_critique_panel,
    emit_stub_implementation_critique_panel,
    emit_stub_module_integrator_critique_panel,
    emit_stub_plan_stage,
    emit_stub_planner_critique_panel,
    emit_stub_self_refinement_critique_panel,
    emit_stub_test_writer_critique_panel,
    execute_agent_evaluator_policy_llm,
    execute_frontend_writer_critique_llm,
    execute_implementation_critique_llm,
    execute_module_integrator_critique_llm,
    execute_plan_stage_llm,
    execute_planner_critique_llm,
    execute_self_refinement_critique_llm,
    execute_test_writer_critique_llm,
)
from nimbusware_orchestrator.merge import load_yaml, policy_snapshot_from_files
from nimbusware_orchestrator.network_resilience_critique import (
    emit_stub_network_resilience_critique_panel,
    execute_network_resilience_critique_llm,
)
from nimbusware_orchestrator.network_resilience_scan import run_network_resilience_scan_summary
from nimbusware_orchestrator.outbound_http import egress_checked_get_for_run
from nimbusware_orchestrator.parallel_writers import WriterStageResult, run_parallel_writer_group
from nimbusware_orchestrator.performance_critique import (
    emit_stub_performance_critique_panel,
    execute_performance_critique_llm,
)
from nimbusware_orchestrator.persona_coverage_critique import (
    emit_stub_persona_coverage_critique_panel,
    execute_persona_coverage_critique_llm,
)
from nimbusware_orchestrator.persona_probation_automation import run_probation_automation
from nimbusware_orchestrator.persona_shelf_auto_create import try_auto_create_persona_if_missing
from nimbusware_orchestrator.persona_shelf_promotion import try_auto_promote_probation_persona
from nimbusware_orchestrator.preflight import run_model_preflight
from nimbusware_orchestrator.refactor_stage import (
    emit_refactor_post_stitch_stage_and_critique,
    emit_refactor_stage_and_critique,
    refactor_post_stitch_gate_failed,
)
from nimbusware_orchestrator.registry import RoleRegistry
from nimbusware_orchestrator.run_dispatch import (
    RunDispatchTask,
    get_run_queue,
    run_dispatch_enabled,
    task_payload_workspace,
)
from nimbusware_orchestrator.scraper_artifacts import (
    resolve_scraper_artifact_base_dir,
)
from nimbusware_orchestrator.scraper_stage import ScraperFetchConfig, load_scraper_fetch_config
from nimbusware_orchestrator.security_critique import (
    emit_stub_security_critique_panel,
    execute_security_critique_llm,
    run_security_scan_summary,
)
from nimbusware_orchestrator.security_scan import run_security_scan, security_scan_tool_summary
from nimbusware_orchestrator.stage_graph import (
    event_metadata_for_stage,
    parallel_group_members,
    stage_graph_from_run_created_metadata,
    stage_graph_from_workflow_profile,
    stage_graph_metadata_snapshot,
    stage_graph_node_lookup,
)
from nimbusware_orchestrator.test_writer_stage import run_test_writer_stage
from nimbusware_orchestrator.traceback_router import suggest_owner_role_from_verifier_log
from nimbusware_orchestrator.verifier_escalation import load_escalate_on_first_verifier_failure
from nimbusware_orchestrator.verifiers import run_writer_verifier_bundle
from nimbusware_orchestrator.workflow_agent_evaluator import (
    agent_evaluator_llm_branch_effective,
    agent_evaluator_llm_stub_env_enabled,
    agent_evaluator_production_default_on,
    agent_evaluator_production_llm_fallback_enabled,
    agent_evaluator_rules_derived_llm_evaluation,
    parse_agent_evaluator_workflow_block,
    persona_coverage_critique_effective,
    persona_coverage_critique_llm_branch_effective,
)
from nimbusware_orchestrator.workflow_escalation import parse_escalation_workflow_block
from nimbusware_orchestrator.workflow_integration_adapter_writer import (
    parse_integration_adapter_writer_workflow_block,
)
from nimbusware_orchestrator.workflow_parallel_critics import parallel_critics_enabled
from nimbusware_orchestrator.workflow_parallel_writers import (
    parallel_writers_enabled,
    test_writer_llm_body_enabled,
    test_writer_llm_stub_fallback,
    test_writer_stage_enabled,
)
from nimbusware_orchestrator.workflow_probation_automation import (
    parse_probation_automation_workflow_block,
)
from nimbusware_orchestrator.workflow_profiles import workflow_profile_dict, workflow_profile_path
from nimbusware_orchestrator.workflow_refactor import (
    parse_refactor_workflow_block,
    refactor_stage_effective,
)
from nimbusware_orchestrator.workflow_research import (
    parse_research_workflow_block,
    parse_stitch_workflow_block,
)
from nimbusware_orchestrator.workflow_scan_critique import (
    network_resilience_critique_effective,
    network_resilience_critique_llm_branch_effective,
    parse_network_resilience_critique_workflow_block,
    parse_performance_critique_workflow_block,
    parse_security_critique_workflow_block,
    performance_critique_effective,
    performance_critique_llm_branch_effective,
    security_critique_effective,
    security_critique_llm_branch_effective,
)
from nimbusware_orchestrator.workflow_security import security_scan_metadata_on_verify_enabled
from nimbusware_orchestrator.workflow_self_refinement import (
    parse_self_refinement_workflow_block,
    self_refinement_llm_critique_branch_effective,
    self_refinement_llm_critique_effective_for_run,
    self_refinement_production_ungated_effective,
    self_refinement_ungated_loop_effective,
)
from nimbusware_orchestrator.workflow_universal_critique import (
    EffectiveUniversalCritique,
    effective_universal_critique,
    parse_universal_critique_workflow_block,
    universal_critique_production_default_on,
)
from nimbusware_store.memory import InMemoryEventStore
from nimbusware_store.protocol import EventStore, serialized_event_from_row


def _coerce_samples_ms(raw: Any) -> list[int] | None:
    """Coerce ``evidence['health_latency_samples_ms']`` for payload persistence.

    The preflight evidence dict is loosely typed (``dict[str, Any]``); the
    payload field requires ``list[int] | None`` with non-negative entries.
    Filters defensively so a corrupted upstream entry can't crash
    persistence: returns ``None`` for non-list values, skips non-int / negative
    entries silently, returns ``None`` if every entry was filtered out.
    """
    if not isinstance(raw, list):
        return None
    cleaned: list[int] = []
    for v in raw:
        if isinstance(v, bool) or not isinstance(v, int):
            continue
        if v < 0:
            continue
        cleaned.append(v)
    return cleaned or None


def _agent_evaluator_auto_promote_env_disabled() -> bool:
    from nimbusware_env.env_flags import env_falsy

    return env_falsy("NIMBUSWARE_AGENT_EVALUATOR_AUTO_PROMOTE")


def _agent_evaluator_auto_create_env_disabled() -> bool:
    from nimbusware_env.env_flags import env_falsy

    return env_falsy("NIMBUSWARE_AGENT_EVALUATOR_AUTO_CREATE")


def _self_refinement_stage_marker_env_disabled() -> bool:
    """When ``NIMBUSWARE_SELF_REFINEMENT_STAGE_MARKER`` is ``0``/``false``/``no``, skip marker emit."""
    from nimbusware_env.env_flags import env_falsy

    return env_falsy("NIMBUSWARE_SELF_REFINEMENT_STAGE_MARKER")


def _self_refinement_auto_promote_env_disabled() -> bool:
    from nimbusware_env.env_flags import env_falsy

    return env_falsy("NIMBUSWARE_SELF_REFINEMENT_AUTO_PROMOTE")


_SELF_REFINEMENT_POLICY_STAGE = "self_refinement:policy"
_SELF_REFINEMENT_MAX_ITER_REASON = "self_refinement_max_iterations"


def _self_refinement_marker_count(rows: list[dict[str, Any]]) -> int:
    return sum(
        1
        for r in rows
        if r.get("event_type") == EventType.STAGE_STARTED.value
        and (r.get("payload") or {}).get("stage_name") == _SELF_REFINEMENT_POLICY_STAGE
    )


def _last_self_refinement_loop_should_continue(rows: list[dict[str, Any]]) -> bool:
    signals = [
        r for r in rows if r.get("event_type") == EventType.SELF_REFINEMENT_LOOP_SIGNALLED.value
    ]
    if not signals:
        return False
    last = max(signals, key=lambda x: int(x["store_seq"]))
    pl = last.get("payload") or {}
    return bool(pl.get("should_continue")) and pl.get("gate_decision") == "proceed"


def _self_refinement_max_iterations_exceeded(rows: list[dict[str, Any]]) -> bool:
    return any(
        r.get("event_type") == EventType.STAGE_FAILED.value
        and (r.get("payload") or {}).get("reason_code") == _SELF_REFINEMENT_MAX_ITER_REASON
        for r in rows
    )


def _persona_id_from_assignment_slot(raw: object) -> str | None:
    if isinstance(raw, str):
        rid = raw.strip()
        return rid or None
    if isinstance(raw, dict):
        val = raw.get("id")
        if val is None:
            val = raw.get("persona_id")
        if val is not None:
            rid = str(val).strip()
            return rid or None
    return None


def optional_tri_allows_emit(tri: str | None) -> bool:
    return tri != "off"


def optional_rows_and_profile(host: Any, run_id: UUID) -> tuple[list[dict[str, Any]], str]:
    rows = host._store.list_run_events(str(run_id))
    wf = workflow_profile_from_run_created_rows(rows) or ""
    return rows, wf


def optional_meta_section(host: Any, run_id: UUID, key: str) -> dict[str, Any]:
    meta = host._run_created_metadata(run_id)
    return mapping_or_empty(meta.get(key))


def gate_fail_for_stage(rows: list[dict[str, Any]], stage_name: str) -> bool:
    for row in reversed(rows):
        if row.get("event_type") != EventType.GATE_DECISION_EMITTED.value:
            continue
        pl = mapping_or_empty(row.get("payload"))
        if pl.get("stage_name") != stage_name:
            continue
        return str(pl.get("verdict", "")).upper() == "FAIL"
    return False


def ollama_runtime_from_host(host: Any) -> tuple[str, float]:
    runtime = mapping_or_empty(host._base_cfg().get("runtime"))
    return (
        str(runtime.get("base_url", "http://localhost:11434")),
        float(runtime.get("request_timeout_seconds", 120)),
    )


__all__ = (
    "AgentEvaluator",
    "Any",
    "EffectiveUniversalCritique",
    "EgressResponseTooLarge",
    "EventStore",
    "EventType",
    "FRONTEND_WRITER_CRITIQUE_STAGE",
    "FindingCreatedEvent",
    "FindingCreatedPayload",
    "FindingFixStrictnessSettings",
    "GateDecisionEmittedEvent",
    "GateDecisionEmittedPayload",
    "IMPLEMENTATION_CRITIQUE_STAGE",
    "InMemoryEventStore",
    "Literal",
    "mapping_or_empty",
    "MODULE_INTEGRATOR_CRITIQUE_STAGE",
    "optional_meta_section",
    "optional_rows_and_profile",
    "optional_tri_allows_emit",
    "ModelPreflightPassedEvent",
    "ModelPreflightPassedPayload",
    "ModelPreflightStartedEvent",
    "ModelPreflightStartedPayload",
    "ModelSelectedFallbackEvent",
    "ModelSelectedFallbackPayload",
    "ModelSelectedPrimaryEvent",
    "ModelSelectedPrimaryPayload",
    "PLANNER_CRITIQUE_STAGE",
    "Path",
    "RoleRegistry",
    "RunCreatedEvent",
    "RunCreatedPayload",
    "RunDispatchTask",
    "RunStartedEvent",
    "RunStartedPayload",
    "ScraperFetchConfig",
    "SelfRefinementEvaluator",
    "SelfRefinementLoopSignalledEvent",
    "SelfRefinementLoopSignalledPayload",
    "SelfRefinementPolicy",
    "Severity",
    "StageFailedEvent",
    "StageFailedPayload",
    "StagePassedEvent",
    "StagePassedPayload",
    "StageStartedEvent",
    "StageStartedPayload",
    "TEST_WRITER_CRITIQUE_STAGE",
    "UUID",
    "Verdict",
    "WriterStageResult",
    "agent_evaluator_llm_branch_effective",
    "agent_evaluator_llm_stub_env_enabled",
    "agent_evaluator_production_default_on",
    "agent_evaluator_production_llm_fallback_enabled",
    "agent_evaluator_rules_derived_llm_evaluation",
    "agent_evaluator_score_band",
    "annotations",
    "append_run_escalated",
    "assert_agent_evaluator_persona_in_shelves",
    "assert_bundle_catalog_maps_resolve",
    "assert_critique_coverage_complete",
    "assert_known_workflow",
    "assert_persona_shelves_valid",
    "assert_stage_graph_valid",
    "assert_taxonomy_keys_resolve",
    "asyncio",
    "critique_coverage_snapshot",
    "datetime",
    "effective_integrator_min_score_to_pass",
    "effective_universal_critique",
    "egress_checked_get_for_run",
    "emit_live_integration_adapter_writer_stage",
    "emit_refactor_post_stitch_stage_and_critique",
    "emit_refactor_stage_and_critique",
    "emit_stub_frontend_writer_critique_panel",
    "emit_stub_implementation_critique_panel",
    "emit_stub_integration_adapter_writer_stage",
    "emit_stub_module_integrator_critique_panel",
    "emit_stub_network_resilience_critique_panel",
    "emit_stub_performance_critique_panel",
    "emit_stub_persona_coverage_critique_panel",
    "emit_stub_plan_stage",
    "emit_stub_planner_critique_panel",
    "emit_stub_security_critique_panel",
    "emit_stub_self_refinement_critique_panel",
    "emit_stub_test_writer_critique_panel",
    "env_str",
    "env_tri_state",
    "env_truthy",
    "event_metadata_for_stage",
    "execute_agent_evaluator_policy_llm",
    "execute_frontend_writer_critique_llm",
    "execute_implementation_critique_llm",
    "execute_module_integrator_critique_llm",
    "execute_network_resilience_critique_llm",
    "execute_performance_critique_llm",
    "execute_persona_coverage_critique_llm",
    "execute_plan_stage_llm",
    "execute_planner_critique_llm",
    "execute_security_critique_llm",
    "execute_self_refinement_critique_llm",
    "execute_test_writer_critique_llm",
    "fast_slice_env_effective",
    "fast_slice_skips_optional_critique_matrix",
    "gate_fail_for_stage",
    "get_run_queue",
    "hashlib",
    "nimbusware_outbound_fetch_enabled",
    "nimbusware_use_llm_enabled",
    "ollama_runtime_from_host",
    "httpx",
    "integration_adapter_writer_stage_would_emit",
    "integrator_gate_workflow_enabled",
    "load_anti_deadlock_settings",
    "load_auto_escalate_after_cumulative_findings",
    "load_bundle_tags_for_bundle_id",
    "load_bundle_title_for_bundle_id",
    "load_critique_router",
    "load_escalate_after_cumulative_gate_failures",
    "load_escalate_after_cumulative_high_severity_findings",
    "load_escalate_after_cumulative_stage_failures",
    "load_escalate_on_first_verifier_failure",
    "load_integrator_gate_emit_enabled",
    "load_notice_escalate_at_cumulative_findings",
    "load_scraper_fetch_config",
    "load_self_refinement_policy",
    "load_yaml",
    "max_open_finding_severity",
    "network_resilience_critique_effective",
    "network_resilience_critique_llm_branch_effective",
    "os",
    "parallel_group_members",
    "parallel_critics_enabled",
    "parallel_writers_enabled",
    "parse_agent_evaluator_workflow_block",
    "parse_escalation_workflow_block",
    "parse_integration_adapter_writer_workflow_block",
    "parse_integrator_gate_project_tags",
    "parse_network_resilience_critique_workflow_block",
    "parse_performance_critique_workflow_block",
    "parse_probation_automation_workflow_block",
    "parse_refactor_workflow_block",
    "parse_research_workflow_block",
    "parse_security_critique_workflow_block",
    "parse_self_refinement_workflow_block",
    "parse_stitch_workflow_block",
    "parse_universal_critique_workflow_block",
    "performance_critique_effective",
    "performance_critique_llm_branch_effective",
    "persona_coverage_critique_effective",
    "persona_coverage_critique_llm_branch_effective",
    "policy_snapshot_from_files",
    "rank_bundle_compatibility_candidates",
    "refactor_post_stitch_gate_failed",
    "refactor_stage_effective",
    "resolve_scraper_artifact_base_dir",
    "run_dispatch_enabled",
    "run_model_preflight",
    "run_network_resilience_scan_summary",
    "run_parallel_writer_group",
    "run_probation_automation",
    "run_security_scan",
    "run_security_scan_summary",
    "run_test_writer_stage",
    "run_frontend_writer_stage",
    "run_writer_verifier_bundle",
    "security_critique_effective",
    "security_critique_llm_branch_effective",
    "security_scan_metadata_on_verify_enabled",
    "security_scan_tool_summary",
    "select_bundle_id_for_workflow",
    "self_refinement_llm_critique_branch_effective",
    "self_refinement_llm_critique_effective_for_run",
    "self_refinement_production_ungated_effective",
    "self_refinement_ungated_loop_effective",
    "serialized_event_from_row",
    "should_emit_anti_deadlock_escalation",
    "stage_graph_from_run_created_metadata",
    "stage_graph_from_workflow_profile",
    "stage_graph_metadata_snapshot",
    "stage_graph_node_lookup",
    "suggest_owner_role_from_verifier_log",
    "task_payload_workspace",
    "taxonomy_keys_for_run_lifecycle",
    "test_writer_llm_body_enabled",
    "test_writer_llm_stub_fallback",
    "test_writer_stage_enabled",
    "time",
    "timezone",
    "try_auto_create_persona_if_missing",
    "try_auto_promote_probation_persona",
    "universal_critique_production_default_on",
    "urlparse",
    "uuid4",
    "validate_event_dict",
    "workflow_profile_dict",
    "workflow_profile_from_run_created_rows",
    "workflow_profile_path",
)

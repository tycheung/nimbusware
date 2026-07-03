from __future__ import annotations

from agent_core.stage_graph import (
    event_metadata_for_stage,
    parallel_group_members,
    stage_graph_from_run_created_metadata,
    stage_graph_from_workflow_profile,
    stage_graph_metadata_snapshot,
    stage_graph_node_lookup,
)
from orchestrator.anti_deadlock import (
    load_anti_deadlock_settings,
    should_emit_anti_deadlock_escalation,
)
from orchestrator.critique.verifier_escalation import load_escalate_on_first_verifier_failure
from orchestrator.escalation_execution import append_run_escalated
from orchestrator.escalation_threshold import (
    load_auto_escalate_after_cumulative_findings,
    load_escalate_after_cumulative_gate_failures,
    load_escalate_after_cumulative_high_severity_findings,
    load_escalate_after_cumulative_stage_failures,
    load_notice_escalate_at_cumulative_findings,
)
from orchestrator.frontend_writer_stage import run_frontend_writer_stage
from orchestrator.ingress import (
    assert_agent_evaluator_persona_in_shelves,
    assert_bundle_catalog_maps_resolve,
    assert_known_workflow,
    assert_persona_shelves_valid,
    assert_stage_graph_valid,
    assert_taxonomy_keys_resolve,
)
from orchestrator.integrator.gate import (
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
from orchestrator.integrator.writer_stage import (
    emit_live_integration_adapter_writer_stage,
    emit_stub_integration_adapter_writer_stage,
    integration_adapter_writer_stage_would_emit,
)
from orchestrator.outbound_http import egress_checked_get_for_run
from orchestrator.parallel_writers import WriterStageResult, run_parallel_writer_group
from orchestrator.persona.probation_automation import run_probation_automation
from orchestrator.persona.shelf_auto_create import try_auto_create_persona_if_missing
from orchestrator.persona.shelf_promotion import try_auto_promote_probation_persona
from orchestrator.preflight import run_model_preflight
from orchestrator.refactor_stage import (
    emit_refactor_post_stitch_stage_and_critique,
    emit_refactor_stage_and_critique,
    refactor_post_stitch_gate_failed,
)
from orchestrator.registry import RoleRegistry
from orchestrator.run_dispatch import (
    RunDispatchTask,
    get_run_queue,
    run_dispatch_enabled,
    task_payload_workspace,
)
from orchestrator.scraper.artifacts import resolve_scraper_artifact_base_dir
from orchestrator.scraper.stage import ScraperFetchConfig, load_scraper_fetch_config
from orchestrator.test_writer_stage import run_test_writer_stage
from orchestrator.traceback_router import suggest_owner_role_from_verifier_log
from orchestrator.verifiers import run_writer_verifier_bundle
from store.memory import InMemoryEventStore
from store.protocol import EventStore, serialized_event_from_row

__all__ = (
    "EventStore",
    "InMemoryEventStore",
    "RoleRegistry",
    "RunDispatchTask",
    "ScraperFetchConfig",
    "WriterStageResult",
    "append_run_escalated",
    "assert_agent_evaluator_persona_in_shelves",
    "assert_bundle_catalog_maps_resolve",
    "assert_known_workflow",
    "assert_persona_shelves_valid",
    "assert_stage_graph_valid",
    "assert_taxonomy_keys_resolve",
    "effective_integrator_min_score_to_pass",
    "egress_checked_get_for_run",
    "emit_live_integration_adapter_writer_stage",
    "emit_refactor_post_stitch_stage_and_critique",
    "emit_refactor_stage_and_critique",
    "emit_stub_integration_adapter_writer_stage",
    "event_metadata_for_stage",
    "get_run_queue",
    "integration_adapter_writer_stage_would_emit",
    "integrator_gate_workflow_enabled",
    "load_anti_deadlock_settings",
    "load_auto_escalate_after_cumulative_findings",
    "load_bundle_tags_for_bundle_id",
    "load_bundle_title_for_bundle_id",
    "load_escalate_after_cumulative_gate_failures",
    "load_escalate_after_cumulative_high_severity_findings",
    "load_escalate_after_cumulative_stage_failures",
    "load_escalate_on_first_verifier_failure",
    "load_integrator_gate_emit_enabled",
    "load_notice_escalate_at_cumulative_findings",
    "load_scraper_fetch_config",
    "parallel_group_members",
    "parse_integrator_gate_project_tags",
    "rank_bundle_compatibility_candidates",
    "refactor_post_stitch_gate_failed",
    "resolve_scraper_artifact_base_dir",
    "run_dispatch_enabled",
    "run_frontend_writer_stage",
    "run_model_preflight",
    "run_parallel_writer_group",
    "run_probation_automation",
    "run_test_writer_stage",
    "run_writer_verifier_bundle",
    "select_bundle_id_for_workflow",
    "serialized_event_from_row",
    "should_emit_anti_deadlock_escalation",
    "stage_graph_from_run_created_metadata",
    "stage_graph_from_workflow_profile",
    "stage_graph_metadata_snapshot",
    "stage_graph_node_lookup",
    "suggest_owner_role_from_verifier_log",
    "task_payload_workspace",
    "try_auto_create_persona_if_missing",
    "try_auto_promote_probation_persona",
    "workflow_profile_from_run_created_rows",
)

"""Shared timeline projections for API and console."""

from nimbusware_projections.builders.agent_evaluator import agent_evaluator_timeline_summary
from nimbusware_projections.builders.integrator_gate import (
    integrator_gate_timeline_delta,
    integrator_gate_timeline_entries,
    integrator_gate_timeline_history,
    integrator_gate_timeline_summary,
)
from nimbusware_projections.builders.maker_progress import (
    maker_progress_from_events,
    strip_operator_fields,
)
from nimbusware_projections.builders.preflight import preflight_timeline_summary
from nimbusware_projections.builders.persona_assignment import persona_assignment_timeline_summary
from nimbusware_projections.builders.run_escalated import (
    run_escalated_timeline_delta,
    run_escalated_timeline_entries,
    run_escalated_timeline_history,
    run_escalated_timeline_summary,
)
from nimbusware_projections.builders.scraper_fetch import scraper_fetch_timeline_summary
from nimbusware_projections.builders.security_scan import (
    security_scan_on_verify_timeline_entries,
    security_scan_on_verify_timeline_history,
    security_scan_on_verify_timeline_summary,
)
from nimbusware_projections.builders.self_refinement import (
    self_refinement_marker_timeline_entries,
    self_refinement_marker_timeline_history,
    self_refinement_timeline_summary,
)
from nimbusware_projections.builders.stage_timeline import (
    critic_matrix_live_timeline_summary,
    parallel_writer_groups_timeline_summary,
    stage_graph_timeline_summary,
)
from nimbusware_projections.builders.universal_critique import (
    universal_critique_effective_from_run_created_metadata,
    universal_critique_timeline_entries,
    universal_critique_timeline_summary,
)
from nimbusware_projections.fields.agent_evaluator import AGENT_EVALUATOR_SUMMARY_KEYS
from nimbusware_projections.fields.integrator_gate import (
    INTEGRATOR_GATE_DISPLAY_FIELDS,
    INTEGRATOR_GATE_ROW_KEYS,
)
from nimbusware_projections.fields.run_escalated import (
    RUN_ESCALATED_DISPLAY_FIELDS,
    RUN_ESCALATED_ROW_KEYS,
)
from nimbusware_projections.fields.scraper_fetch import SCRAPER_FETCH_ROW_KEYS
from nimbusware_projections.fields.security_scan import SECURITY_SCAN_ROW_KEYS
from nimbusware_projections.fields.self_refinement import SELF_REFINEMENT_SUMMARY_KEYS

__all__ = [
    "AGENT_EVALUATOR_SUMMARY_KEYS",
    "INTEGRATOR_GATE_DISPLAY_FIELDS",
    "INTEGRATOR_GATE_ROW_KEYS",
    "RUN_ESCALATED_DISPLAY_FIELDS",
    "RUN_ESCALATED_ROW_KEYS",
    "SCRAPER_FETCH_ROW_KEYS",
    "SECURITY_SCAN_ROW_KEYS",
    "SELF_REFINEMENT_SUMMARY_KEYS",
    "agent_evaluator_timeline_summary",
    "critic_matrix_live_timeline_summary",
    "integrator_gate_timeline_delta",
    "integrator_gate_timeline_entries",
    "integrator_gate_timeline_history",
    "integrator_gate_timeline_summary",
    "maker_progress_from_events",
    "strip_operator_fields",
    "parallel_writer_groups_timeline_summary",
    "persona_assignment_timeline_summary",
    "preflight_timeline_summary",
    "run_escalated_timeline_delta",
    "run_escalated_timeline_entries",
    "run_escalated_timeline_history",
    "run_escalated_timeline_summary",
    "scraper_fetch_timeline_summary",
    "security_scan_on_verify_timeline_entries",
    "security_scan_on_verify_timeline_history",
    "security_scan_on_verify_timeline_summary",
    "self_refinement_marker_timeline_entries",
    "self_refinement_marker_timeline_history",
    "self_refinement_timeline_summary",
    "stage_graph_timeline_summary",
    "universal_critique_effective_from_run_created_metadata",
    "universal_critique_timeline_entries",
    "universal_critique_timeline_summary",
]

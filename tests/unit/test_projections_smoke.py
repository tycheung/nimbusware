from __future__ import annotations

from projections.builders import maker_progress, preflight, scraper_fetch, stage_timeline
from projections.builders.agent_evaluator import agent_evaluator_timeline_summary
from projections.builders.integrator_gate import (
    integrator_gate_timeline_delta,
    integrator_gate_timeline_entries,
    integrator_gate_timeline_history,
    integrator_gate_timeline_summary,
)
from projections.builders.persona_assignment import persona_assignment_timeline_summary
from projections.builders.run_escalated import run_escalated_timeline_summary
from projections.builders.security_scan import security_scan_on_verify_timeline_summary
from projections.builders.self_refinement import self_refinement_timeline_summary
from projections.builders.universal_critique import universal_critique_timeline_summary


def test_projection_builders_empty_rows() -> None:
    assert agent_evaluator_timeline_summary([]) is None
    assert integrator_gate_timeline_summary([]) is None
    assert integrator_gate_timeline_entries([]) == []
    assert integrator_gate_timeline_history([]) == []
    assert integrator_gate_timeline_delta([]) is None
    assert security_scan_on_verify_timeline_summary([]) is None
    assert self_refinement_timeline_summary([]) is None
    assert universal_critique_timeline_summary([]) is None
    assert persona_assignment_timeline_summary([]) is None
    assert run_escalated_timeline_summary([]) is None
    assert preflight.preflight_timeline_summary([]) is None
    assert stage_timeline.stage_graph_timeline_summary([]) is None
    assert stage_timeline.parallel_writer_groups_timeline_summary([]) is None
    assert stage_timeline.critic_matrix_live_timeline_summary([]) is None
    assert scraper_fetch.scraper_fetch_timeline_summary([]) is None
    assert isinstance(maker_progress.maker_progress_from_events([]), dict)


def test_maker_slice_workflow_public_api() -> None:
    from maker.slice_workflow import (
        apply_pending_slice,
        approve_run_plan,
        get_pending_state,
        prepare_next_pending_slice,
        revert_workspace,
        skip_pending_slice,
    )

    assert callable(apply_pending_slice)
    assert callable(approve_run_plan)
    assert callable(get_pending_state)
    assert callable(prepare_next_pending_slice)
    assert callable(revert_workspace)
    assert callable(skip_pending_slice)

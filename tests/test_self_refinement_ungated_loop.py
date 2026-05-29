from __future__ import annotations

import os
from unittest.mock import patch

from hermes_api.routes.runs import self_refinement_timeline_summary
from hermes_orchestrator.pipeline import make_dev_orchestrator


@patch.dict(os.environ, {"HERMES_SELF_REFINEMENT_STAGE_MARKER": "1"}, clear=False)
def test_self_refinement_ungated_loop_forces_proceed() -> None:
    orch, mem = make_dev_orchestrator()
    rid = orch.create_run("self_refinement_ungated_on")
    with patch.dict(os.environ, {"HERMES_SELF_REFINEMENT_UNGATED_LOOP": "1"}, clear=False):
        orch._maybe_emit_self_refinement_stage_marker(rid)  # noqa: SLF001
    signal = next(
        r
        for r in mem.list_run_events(str(rid))
        if r.get("event_type") == "self_refinement.loop.signalled"
    )
    assert (signal.get("payload") or {}).get("gate_decision") == "proceed"
    assert (signal.get("payload") or {}).get("should_continue") is True
    assert isinstance((signal.get("payload") or {}).get("iteration_progress_ratio"), float)
    marker = next(
        r
        for r in mem.list_run_events(str(rid))
        if r.get("event_type") == "stage.started"
        and (r.get("payload") or {}).get("stage_name") == "self_refinement:policy"
    )
    sr_meta = ((marker.get("metadata") or {}).get("self_refinement") or {})
    assert sr_meta.get("gate_decision") == "proceed"
    assert isinstance(sr_meta.get("loops_remaining"), int)
    assert isinstance(sr_meta.get("iteration_progress_ratio"), float)
    assert sr_meta.get("should_continue") is True
    sr = self_refinement_timeline_summary(list(mem.list_run_events(str(rid))))
    assert sr is not None
    assert sr.get("loop_signal_count") == 1


@patch.dict(os.environ, {"HERMES_SELF_REFINEMENT_STAGE_MARKER": "1"}, clear=False)
def test_self_refinement_ungated_loop_multi_iteration_progression() -> None:
    orch, mem = make_dev_orchestrator()
    rid = orch.create_run("self_refinement_ungated_on")
    with patch.dict(os.environ, {"HERMES_SELF_REFINEMENT_UNGATED_LOOP": "1"}, clear=False):
        orch._maybe_emit_self_refinement_stage_marker(rid)  # noqa: SLF001
        orch._maybe_emit_self_refinement_stage_marker(rid)  # noqa: SLF001
    phase_d = [
        r
        for r in mem.list_run_events(str(rid))
        if r.get("event_type") == "self_refinement.loop.signalled"
    ]
    assert len(phase_d) == 2
    assert (phase_d[0].get("payload") or {}).get("signal") == "phase_d_kickoff"
    assert (phase_d[1].get("payload") or {}).get("signal") == "phase_d_iteration"
    assert (phase_d[1].get("payload") or {}).get("attempt") == 2
    assert (phase_d[1].get("payload") or {}).get("should_continue") is True
    sr = self_refinement_timeline_summary(list(mem.list_run_events(str(rid))))
    assert sr is not None
    assert sr.get("ungated_loop") is True
    assert sr.get("loop_signal_count") == 2
    assert sr.get("ungated_iteration_count") == 1

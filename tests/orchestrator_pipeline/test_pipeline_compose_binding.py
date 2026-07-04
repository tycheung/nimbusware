from __future__ import annotations

from unittest.mock import patch

from orchestrator.pipeline import RunOrchestrator, make_dev_orchestrator


def test_pipeline_verify_delegates_to_micro_slice_pass() -> None:
    orch, _mem = make_dev_orchestrator()
    assert isinstance(orch, RunOrchestrator)
    run_id = orch.create_run("default")

    with (
        patch.object(orch, "execute_micro_slice_pass") as mock_ms,
        patch.object(orch, "_run_writer_group_dispatch") as mock_writers,
        patch.object(orch, "_run_post_writer_critique_tail") as mock_tail,
    ):
        orch.execute_writer_verifier_pass(run_id)
    mock_ms.assert_called_once()
    mock_writers.assert_called_once()
    mock_tail.assert_called_once()

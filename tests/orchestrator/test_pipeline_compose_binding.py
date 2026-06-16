from __future__ import annotations

from unittest.mock import patch

from nimbusware_orchestrator.pipeline import RunOrchestrator, make_dev_orchestrator


def test_pipeline_patch_reaches_mixin_method() -> None:
    orch, _mem = make_dev_orchestrator()
    assert isinstance(orch, RunOrchestrator)
    run_id = orch.create_run("default")

    seen: list[str] = []

    def _stub_bundle(*_args: object, **_kwargs: object) -> tuple[int, str]:
        seen.append("stub")
        return 0, "ok"

    with patch(
        "nimbusware_orchestrator.pipeline.run_writer_verifier_bundle",
        side_effect=_stub_bundle,
    ):
        orch.execute_writer_verifier_pass(run_id)

    assert seen == ["stub"]

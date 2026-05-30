from __future__ import annotations

import os
from unittest.mock import patch

from hermes_orchestrator.pipeline import make_dev_orchestrator


@patch.dict(os.environ, {"HERMES_STUB_IMPLEMENTATION_CRITICS": "1"}, clear=False)
def test_default_profile_enforces_unanimous_gate() -> None:
    orch, mem = make_dev_orchestrator()
    rid = orch.create_run("default")
    with patch("hermes_orchestrator.pipeline.run_writer_verifier_bundle", return_value=(0, "ok")):
        orch.execute_writer_verifier_pass(rid)
    gates = [
        r
        for r in mem.list_run_events(str(rid))
        if r.get("event_type") == "gate.decision.emitted"
        and (r.get("payload") or {}).get("stage_name") == "implementation.critique"
    ]
    assert gates
    assert (gates[-1].get("payload") or {}).get("unanimous_pass_required") is True


@patch.dict(
    os.environ,
    {"HERMES_STUB_IMPLEMENTATION_CRITICS": "1", "HERMES_UNANIMOUS_GATE_ENFORCE": "0"},
    clear=False,
)
def test_env_override_can_disable_unanimous_gate() -> None:
    orch, mem = make_dev_orchestrator()
    rid = orch.create_run("default")
    with patch("hermes_orchestrator.pipeline.run_writer_verifier_bundle", return_value=(0, "ok")):
        orch.execute_writer_verifier_pass(rid)
    run_created = next(
        r for r in mem.list_run_events(str(rid)) if r.get("event_type") == "run.created"
    )
    uce = (run_created.get("metadata") or {}).get("universal_critique_effective") or {}
    assert uce.get("unanimous_gate_enforce") is False

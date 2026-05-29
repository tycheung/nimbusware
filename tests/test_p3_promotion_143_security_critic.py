"""fo143 promotion: security critique blocks downstream critique on gate FAIL."""


from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from hermes_orchestrator.llm_plan import IMPLEMENTATION_CRITIQUE_STAGE
from hermes_orchestrator.pipeline import make_dev_orchestrator
from hermes_orchestrator.security_critique import SECURITY_CRITIQUE_STAGE


def test_security_gate_fail_skips_implementation_critique(monkeypatch: pytest.MonkeyPatch) -> None:
    repo = Path(__file__).resolve().parents[1]
    orch, store = make_dev_orchestrator(repo)
    run_id = orch.create_run("security_critique_on")

    monkeypatch.setattr(
        "hermes_orchestrator.pipeline.run_writer_verifier_bundle",
        lambda ws: (0, "ok\n"),
    )
    monkeypatch.setattr(
        "hermes_orchestrator.pipeline.run_security_scan_summary",
        lambda ws: {
            "security_scan_tools": {"ruff": 1, "bandit": 0, "mypy": 0},
            "security_scan_exit": 1,
        },
    )

    orch.execute_writer_verifier_pass(run_id, workspace=repo)
    rows = store.list_run_events(str(run_id))
    stage_names = [
        (r.get("payload") or {}).get("stage_name")
        for r in rows
        if r.get("event_type") == "stage.started"
    ]
    assert SECURITY_CRITIQUE_STAGE in stage_names
    assert IMPLEMENTATION_CRITIQUE_STAGE not in stage_names

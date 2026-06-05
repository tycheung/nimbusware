"""Escalation on first verifier failure (policy YAML)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from agent_core.models import EventType
from nimbusware_env import find_repo_root
from nimbusware_orchestrator.pipeline import make_dev_orchestrator
from nimbusware_orchestrator.verifier_escalation import load_escalate_on_first_verifier_failure


def test_load_escalate_on_first_verifier_failure_default() -> None:
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    assert load_escalate_on_first_verifier_failure(root) is False


def test_verifier_failure_checkpoint_once() -> None:
    with patch(
        "nimbusware_orchestrator.pipeline.load_escalate_on_first_verifier_failure",
        return_value=True,
    ):
        orch, mem = make_dev_orchestrator()
        rid = orch.create_run("default")
        orch._maybe_escalate_verifier_failure_checkpoint(rid)  # noqa: SLF001
        esc = [
            r
            for r in mem.list_run_events(str(rid))
            if r["event_type"] == EventType.RUN_ESCALATED.value
        ]
        assert len(esc) == 1
        orch._maybe_escalate_verifier_failure_checkpoint(rid)  # noqa: SLF001
        esc2 = [
            r
            for r in mem.list_run_events(str(rid))
            if r["event_type"] == EventType.RUN_ESCALATED.value
        ]
        assert len(esc2) == 1

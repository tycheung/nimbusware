from __future__ import annotations

from uuid import uuid4

from hermes_orchestrator.ci_bridge.external_ci import notify_gate_decision_external


def test_external_ci_skipped_without_token(monkeypatch) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("HERMES_CI_GITHUB_REPO", raising=False)
    out = notify_gate_decision_external(
        run_id=uuid4(),
        verdict="PASS",
        stage_name="bundle_compatibility",
    )
    assert out["status"] == "skipped"

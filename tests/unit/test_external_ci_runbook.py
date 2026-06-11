from __future__ import annotations

from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_RUNBOOK = _REPO / "docs" / "deploy" / "external-ci-bridge.md"


def test_external_ci_runbook_exists_and_documents_env() -> None:
    text = _RUNBOOK.read_text(encoding="utf-8")
    assert "GITHUB_TOKEN" in text
    assert "NIMBUSWARE_CI_GITHUB_REPO" in text
    assert "NIMBUSWARE_GITLAB_TOKEN" in text
    assert "NIMBUSWARE_CI_GITLAB_PROJECT" in text
    assert "notify_gate_decision_external" in text
    assert "slice.gate" in text
    assert "factory.gate" in text

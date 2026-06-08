from __future__ import annotations

from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_RUNBOOK = _REPO / "docs" / "deploy" / "enterprise-integrator-runbook.md"


def test_enterprise_integrator_runbook_exists_and_documents_gate() -> None:
    text = _RUNBOOK.read_text(encoding="utf-8")
    assert "NIMBUSWARE_EMIT_INTEGRATOR_GATE" in text
    assert "NIMBUSWARE_INTEGRATOR_PROBE_MAX_ATTEMPTS" in text
    assert "integrator_live_context" in text
    assert "external-ci-bridge.md" in text
    assert "gate.decision.emitted" in text

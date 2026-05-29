"""Escalation hooks tied to writer verifier outcomes."""

from __future__ import annotations

from pathlib import Path

from hermes_orchestrator.merge import load_yaml


def load_escalate_on_first_verifier_failure(repo_root: Path) -> bool:
    """When true, emit one ``run.escalated`` after the first verifier ``finding.created``."""
    path = repo_root / "configs" / "escalation" / "policy.yaml"
    if not path.is_file():
        return False
    raw = load_yaml(path)
    ver = raw.get("verification")
    if not isinstance(ver, dict):
        return False
    v = ver.get("escalate_on_first_verifier_failure")
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip().lower() in ("1", "true", "yes", "on")
    return False

"""Escalation / anti-deadlock policy snapshot (plan §14 #19)."""
from __future__ import annotations
from pathlib import Path
from typing import Any
from hermes_orchestrator.merge import load_yaml
class EscalationPolicy:
    def __init__(self, policy_path: Path) -> None:
        self._raw = load_yaml(policy_path)
    def as_dict(self) -> dict[str, Any]:
        return dict(self._raw)

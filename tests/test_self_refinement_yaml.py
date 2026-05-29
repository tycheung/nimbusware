"""Self-refinement policy YAML (plan §14 #17)."""

from __future__ import annotations

from pathlib import Path

from hermes_extensions import load_self_refinement_policy

ROOT = Path(__file__).resolve().parents[1]


def test_load_self_refinement_policy() -> None:
    pol = load_self_refinement_policy(ROOT / "configs" / "self_refinement" / "policy.yaml")
    assert pol.version == 1
    assert pol.enabled is False
    assert "event_type" in pol.description.lower()

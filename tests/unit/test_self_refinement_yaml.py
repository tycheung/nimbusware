"""Self-refinement policy YAML ."""

from __future__ import annotations

from pathlib import Path

from nimbusware_env import find_repo_root
from nimbusware_extensions import load_self_refinement_policy

ROOT = find_repo_root(start=Path(__file__).resolve().parents[1])


def test_load_self_refinement_policy() -> None:
    pol = load_self_refinement_policy(ROOT / "configs" / "self_refinement" / "policy.yaml")
    assert pol.version == 1
    assert pol.enabled is False
    assert "event_type" in pol.description.lower()

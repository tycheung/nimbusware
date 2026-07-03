from __future__ import annotations

from pathlib import Path

from env import find_repo_root
from extensions import load_self_refinement_policy

ROOT = find_repo_root(start=Path(__file__).resolve().parents[1])


def test_load_self_refinement_policy() -> None:
    pol = load_self_refinement_policy(ROOT / "configs" / "self_refinement" / "policy.yaml")
    assert pol.version == 1
    assert pol.enabled is False
    assert "event_type" in pol.description.lower()

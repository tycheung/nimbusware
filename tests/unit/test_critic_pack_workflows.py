from __future__ import annotations

from pathlib import Path

from orchestrator.critic_pack_resolve import list_workflows_using_critic_pack

REPO = Path(__file__).resolve().parents[2]


def test_list_workflows_using_default_security_pack() -> None:
    profiles = list_workflows_using_critic_pack(REPO, "default-security")
    assert isinstance(profiles, list)


def test_list_workflows_unknown_pack_returns_empty() -> None:
    assert list_workflows_using_critic_pack(REPO, "does-not-exist-pack-xyz") == []

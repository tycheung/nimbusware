"""Traceback / log taxonomy hints → registry ``role_id``."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from nimbusware_orchestrator.registry import RoleRegistry
from nimbusware_orchestrator.traceback_router import suggest_owner_role_from_verifier_log
from nimbusware_env import find_repo_root

ROOT = find_repo_root(start=Path(__file__).resolve().parents[1])


def test_known_taxonomy_in_log_resolves() -> None:
    reg = RoleRegistry.from_yaml(ROOT / "configs" / "roles.yaml")
    log = "Traceback ... role backend_writer failed assertion ..."
    owner = suggest_owner_role_from_verifier_log(log, reg)
    assert owner == UUID("44444444-4444-4444-8444-444444444404")


def test_unknown_label_returns_none() -> None:
    reg = RoleRegistry.from_yaml(ROOT / "configs" / "roles.yaml")
    log = "no taxonomy keys in this log"
    assert suggest_owner_role_from_verifier_log(log, reg) is None

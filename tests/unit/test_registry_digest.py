"""Role registry YAML version + content digest."""

from __future__ import annotations

from pathlib import Path

from nimbusware_orchestrator.registry import RoleRegistry
from nimbusware_env import find_repo_root

ROOT = find_repo_root(start=Path(__file__).resolve().parents[1])


def test_roles_yaml_has_version_and_digest() -> None:
    reg = RoleRegistry.from_yaml(ROOT / "configs" / "roles.yaml")
    assert reg.yaml_version >= 1
    assert reg.content_digest_sha256_16
    assert len(reg.content_digest_sha256_16) == 16

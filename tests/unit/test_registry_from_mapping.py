"""RoleRegistry programmatic mapping (DB adapter hook)."""

from __future__ import annotations

from uuid import UUID

from nimbusware_orchestrator.registry import RoleRegistry


def test_from_mapping_normalizes_keys() -> None:
    reg = RoleRegistry.from_mapping(
        {"Planner": UUID("11111111-1111-4111-8111-111111111101")},
        yaml_version=9,
        content_digest_sha256_16="abc",
    )
    assert reg.resolve("planner") == UUID("11111111-1111-4111-8111-111111111101")
    assert reg.yaml_version == 9
    assert reg.content_digest_sha256_16 == "abc"

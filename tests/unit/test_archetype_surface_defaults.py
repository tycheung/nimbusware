from __future__ import annotations

from nimbusware_maker.archetype_surface_defaults import (
    apply_fleet_surface_policy,
    campaign_profile_for_archetype,
    default_surfaces_for_archetype,
    manifest_for_archetype,
)


def test_default_surfaces_include_web_for_all_archetypes() -> None:
    for bundle in ("default", "enterprise"):
        surfaces = default_surfaces_for_archetype(setup_bundle=bundle, archetype="safe_coding")
        assert "web" in surfaces
        assert "api" in surfaces


def test_fleet_policy_restores_web_surface() -> None:
    manifest = {"surfaces": ["api"], "stacks": {"api": "fastapi_python"}}
    adjusted = apply_fleet_surface_policy(manifest, {"require_web_surface": True})
    assert "web" in adjusted["surfaces"]
    assert "web" in adjusted["stacks"]


def test_campaign_profile_narrowed_uses_micro_slice() -> None:
    assert campaign_profile_for_archetype(scope_narrowed=True) == "campaign_micro_slice"


def test_campaign_profile_fullstack_default() -> None:
    assert campaign_profile_for_archetype(archetype="safe_coding") == "campaign_fullstack"
    assert campaign_profile_for_archetype(setup_bundle="enterprise") == "campaign_fullstack"


def test_manifest_for_archetype_has_both_surfaces() -> None:
    manifest = manifest_for_archetype(setup_bundle="enterprise", archetype="a3")
    assert manifest["surfaces"] == ["api", "web"]

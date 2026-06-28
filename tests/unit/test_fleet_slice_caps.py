from __future__ import annotations

from nimbusware_orchestrator.binding_preflight import (
    build_binding_preflight_report,
    roles_for_stack_manifest,
    surface_stage_map,
)
from nimbusware_orchestrator.fleet_slice_caps import clamp_slice_budget, fleet_replan_metadata


def test_clamp_slice_budget_enterprise() -> None:
    files, loc, active = clamp_slice_budget(
        5,
        200,
        tenant_slug="default",
        setup_bundle="enterprise",
    )
    assert files == 3
    assert loc == 120
    assert active is True


def test_fleet_replan_metadata() -> None:
    meta = fleet_replan_metadata(fleet_cap_active=True)
    assert meta.get("fleet_cap_triggered") == "true"
    assert "fleet_cap_cta" in meta


def test_binding_preflight_manifest_surface_map() -> None:
    manifest = {
        "surfaces": ["api", "web"],
        "stacks": {"api": "fastapi_python", "web": "react_vite"},
    }
    roles = roles_for_stack_manifest(manifest)
    assert "backend_writer" in roles
    assert "frontend_writer" in roles
    stage_map = surface_stage_map(manifest)
    assert stage_map.get("api") == "backend_writer"
    assert stage_map.get("web") == "frontend_writer"

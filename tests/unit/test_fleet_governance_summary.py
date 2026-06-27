from __future__ import annotations

from nimbusware_maker.fleet_governance_summary import fleet_governance_summary


def test_fleet_governance_summary_enterprise() -> None:
    body = fleet_governance_summary(setup_bundle="enterprise", archetype="a3")
    assert body["mandatory_discovery"] is True
    assert "web" in body["default_surfaces"]
    assert body["deploy_chain_required"] is True
    assert "enforcement_policy" in body


def test_fleet_governance_summary_default_bundle() -> None:
    body = fleet_governance_summary(setup_bundle="default", archetype="safe_coding")
    assert body["mandatory_discovery"] is False
    assert body["surface_policy"]["require_web_surface"] is False

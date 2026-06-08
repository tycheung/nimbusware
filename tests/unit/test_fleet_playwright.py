from __future__ import annotations

from nimbusware_orchestrator.fleet_playwright import (
    attach_fleet_playwright_capture,
    fleet_playwright_config,
    fleet_playwright_ws_endpoint,
)


def test_fleet_playwright_disabled_by_default(monkeypatch) -> None:
    monkeypatch.delenv("NIMBUSWARE_FLEET_PLAYWRIGHT_WS_ENDPOINT", raising=False)
    assert fleet_playwright_ws_endpoint() is None
    assert fleet_playwright_config() == {"enabled": False}


def test_fleet_playwright_config_when_env_set(monkeypatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_FLEET_PLAYWRIGHT_WS_ENDPOINT", "ws://fleet.example/playwright")
    cfg = fleet_playwright_config()
    assert cfg["enabled"] is True
    assert cfg["ws_endpoint"] == "ws://fleet.example/playwright"


def test_attach_fleet_playwright_capture() -> None:
    capture = attach_fleet_playwright_capture({"playwright_ready": False})
    assert "fleet_playwright" not in capture

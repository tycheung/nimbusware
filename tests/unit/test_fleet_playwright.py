from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

from nimbusware_orchestrator.fleet_playwright import (
    FleetPlaywrightProbe,
    attach_fleet_playwright_capture,
    fleet_browser_goto,
    fleet_playwright_config,
    fleet_playwright_ws_endpoint,
    probe_fleet_playwright_endpoint,
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


def test_probe_fleet_playwright_connects(monkeypatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_FLEET_PLAYWRIGHT_WS_ENDPOINT", "ws://fleet.example/playwright")
    mock_browser = MagicMock()
    mock_browser.version = "1.2.3"
    mock_playwright = MagicMock()
    mock_playwright.chromium.connect.return_value = mock_browser
    mock_cm = MagicMock()
    mock_cm.__enter__.return_value = mock_playwright
    fake_sync_api = MagicMock()
    fake_sync_api.sync_playwright.return_value = mock_cm
    fake_sync_api.Error = Exception
    with patch.dict(sys.modules, {"playwright": MagicMock(), "playwright.sync_api": fake_sync_api}):
        probe = probe_fleet_playwright_endpoint()
    assert probe.enabled is True
    assert probe.connected is True
    mock_browser.close.assert_called_once()


def test_fleet_browser_goto_when_unavailable(monkeypatch) -> None:
    monkeypatch.delenv("NIMBUSWARE_FLEET_PLAYWRIGHT_WS_ENDPOINT", raising=False)
    result = fleet_browser_goto("http://127.0.0.1:8080", "/")
    assert result["ok"] is False


def test_attach_fleet_playwright_capture_includes_probe(monkeypatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_FLEET_PLAYWRIGHT_WS_ENDPOINT", "ws://fleet.example/playwright")
    with patch(
        "nimbusware_orchestrator.fleet_playwright.probe_fleet_playwright_endpoint",
        return_value=FleetPlaywrightProbe(enabled=True, connected=True, detail="ok"),
    ):
        capture = attach_fleet_playwright_capture({"playwright_ready": True})
    assert capture["fleet_playwright"]["connected"] is True

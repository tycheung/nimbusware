"""Enterprise fleet Playwright worker endpoint resolution (fo702 stub)."""

from __future__ import annotations

from typing import Any

from nimbusware_env.env_flags import env_str


def fleet_playwright_ws_endpoint() -> str | None:
    raw = env_str("NIMBUSWARE_FLEET_PLAYWRIGHT_WS_ENDPOINT").strip()
    return raw or None


def fleet_playwright_config() -> dict[str, Any]:
    ws = fleet_playwright_ws_endpoint()
    if not ws:
        return {"enabled": False}
    return {"enabled": True, "ws_endpoint": ws, "mode": "remote_ws"}


def attach_fleet_playwright_capture(capture: dict[str, Any]) -> dict[str, Any]:
    cfg = fleet_playwright_config()
    if cfg.get("enabled"):
        capture["fleet_playwright"] = cfg
    return capture

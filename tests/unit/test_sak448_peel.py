from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def test_home_readiness_miss_banner() -> None:
    """sak448-a."""
    path = (
        Path(__file__).resolve().parents[2]
        / "packages"
        / "maker_web"
        / "static"
        / "js"
        / "tabs"
        / "home_readiness_ui.js"
    )
    text = path.read_text(encoding="utf-8")
    assert "isBrokerMiss" in text
    assert "maker-home-readiness-miss" in text


def test_subscriptions_oauth_no_empty_catch() -> None:
    """sak448-b."""
    path = (
        Path(__file__).resolve().parents[2]
        / "packages"
        / "maker_web"
        / "static"
        / "js"
        / "tabs"
        / "models_subscriptions_ui.js"
    )
    text = path.read_text(encoding="utf-8")
    assert ".catch(() => ({ providers: [] }))" not in text
    assert 'via: "broker_miss"' in text
    assert "toastIfMiss" in text


def test_connections_api_miss_helpers() -> None:
    """sak448-c."""
    path = (
        Path(__file__).resolve().parents[2]
        / "packages"
        / "maker_web"
        / "static"
        / "js"
        / "tabs"
        / "models_connections_ui.js"
    )
    text = path.read_text(encoding="utf-8")
    assert "toastIfMiss" in text
    assert "isBrokerMiss" in text


def test_subscription_oauth_status_openapi() -> None:
    """sak448-d."""
    from api.routes.provider_subscription_oauth import SubscriptionOauthStatusResponse

    assert SubscriptionOauthStatusResponse(providers=[]).providers == []


def test_fleet_workspace_readiness_openapi() -> None:
    """sak448-e."""
    from api.routes.platform import FleetGovernanceResponse, WorkspaceReadinessResponse

    assert FleetGovernanceResponse(setup_bundle="default").setup_bundle == "default"
    assert WorkspaceReadinessResponse(ready=True).ready is True


def test_admin_normalize_status_miss_in_peel_assert() -> None:
    """sak448-f."""
    api = Path(__file__).resolve().parents[2] / "packages" / "admin_ui" / "src" / "api"
    peel = (api / "peel_assert.ts").read_text(encoding="utf-8")
    client = (api / "client.ts").read_text(encoding="utf-8")
    assert "export function normalizeStatusMiss" in peel
    assert "function normalizeStatusMiss" not in client
    assert 'from "./peel_assert"' in client
    assert "normalizeStatusMiss" in client


def test_admin_is_capacity_miss_shared() -> None:
    """sak448-g."""
    root = Path(__file__).resolve().parents[2] / "packages" / "admin_ui" / "src"
    peel = (root / "api" / "peel_assert.ts").read_text(encoding="utf-8")
    hw = (root / "pages" / "HardwarePage.tsx").read_text(encoding="utf-8")
    fleet = (root / "pages" / "FleetPage.tsx").read_text(encoding="utf-8")
    assert "export function isCapacityMiss" in peel
    assert "isCapacityMiss" in hw
    assert "isCapacityMiss" in fleet


def test_review_git_readiness_miss() -> None:
    """sak448-h."""
    path = (
        Path(__file__).resolve().parents[2]
        / "packages"
        / "maker_web"
        / "static"
        / "js"
        / "tabs"
        / "review_git_ui.js"
    )
    text = path.read_text(encoding="utf-8")
    assert "isBrokerMiss" in text
    assert "isBrokerMiss(readiness)" in text


def test_broker_client_health_and_terminate_assert() -> None:
    """sak448-i."""
    from broker_client.client import BrokerClient

    client = BrokerClient(base_url="http://example.test", client=MagicMock())
    with patch(
        "broker_client.client.get_json",
        return_value={"error": "down"},
    ):
        with pytest.raises(RuntimeError, match="broker_miss"):
            client.health()
    with patch(
        "broker_client.client.get_json",
        return_value={"ok": True},
    ):
        assert client.health() == {"ok": True}
    with patch(
        "broker_client.stage_bind.compute.compute_work_via_broker",
        return_value={"error": "nope", "work": None},
    ):
        with pytest.raises(RuntimeError, match="broker_miss"):
            client.terminate_restart_work("w1")

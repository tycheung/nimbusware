from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def _js_root() -> Path:
    return Path(__file__).resolve().parents[2] / "packages" / "maker_web" / "static" / "js"


def test_operator_ribbons_progress_miss() -> None:
    """sak485-a."""
    root = _js_root()
    ribbons = (root / "tabs" / "progress" / "operator-ribbons.js").read_text(encoding="utf-8")
    progress = (root / "tabs" / "progress.js").read_text(encoding="utf-8")
    assert "toastIfMiss" in ribbons
    assert "toastIfMiss" in progress


def test_sse_tab_loader_shell_miss() -> None:
    """sak485-b."""
    root = _js_root()
    sse = (root / "sse-client.js").read_text(encoding="utf-8")
    loader = (root / "tab-loader.js").read_text(encoding="utf-8")
    shell = (root / "app-shell.js").read_text(encoding="utf-8")
    assert "brokerBacked" in sse or "missBannerText" in sse
    assert "toastIfMiss" in loader
    assert "handleRouteLoadError" in loader
    assert "handleRouteLoadError" in shell


def test_chat_agents_run_card_miss() -> None:
    """sak485-c."""
    tabs = _js_root() / "tabs"
    agents = (tabs / "chat_agents_ui.js").read_text(encoding="utf-8")
    card = (tabs / "chat_run_card_ui.js").read_text(encoding="utf-8")
    assert "maker-chat-agents-miss" in agents or "toastIfMiss" in agents
    assert "toastIfMiss" in card or "isBrokerMiss" in card


def test_plan_backlog_miss() -> None:
    """sak485-d."""
    plan = (_js_root() / "tabs" / "plan.js").read_text(encoding="utf-8")
    assert "maker-plan-miss" in plan
    assert "toastIfMiss" in plan


def test_run_findings_learnings_openapi() -> None:
    """sak485-e."""
    from api.routes.runs.detail import RunFindingsResponse
    from api.routes.runs.dev_env import DevEnvTheaterResponse
    from api.routes.runs.learnings import RunLearningsResponse

    assert RunFindingsResponse().via is None
    assert RunLearningsResponse().via is None
    assert DevEnvTheaterResponse().via is None


def test_fleet_analytics_openapi() -> None:
    """sak485-f."""
    from api.routes.enterprise.fleet_analytics import FleetAnalyticsCompareResponse
    from api.routes.enterprise.fleet_critic_reliability import FleetCriticReliabilityResponse
    from api.routes.enterprise.fleet_learnings import FleetLearningsSearchResponse

    assert FleetAnalyticsCompareResponse().via is None
    assert FleetLearningsSearchResponse().via is None
    assert FleetCriticReliabilityResponse().via is None


def test_operator_settings_iam_openapi() -> None:
    """sak485-g."""
    from api.routes.enterprise.iam import IamMeResponse, TenantsListResponse
    from api.routes.operator_settings import SettingsScopeResponse

    assert SettingsScopeResponse().via is None
    assert IamMeResponse().via is None
    assert TenantsListResponse().via is None


def test_admin_fleet_peel_deepen() -> None:
    """sak485-h."""
    root = Path(__file__).resolve().parents[2] / "packages" / "admin_ui" / "src"
    fleet = (root / "pages" / "FleetPage.tsx").read_text(encoding="utf-8")
    compliance = (root / "pages" / "fleet" / "FleetCompliancePanel.tsx").read_text(encoding="utf-8")
    assert "peelUnavailable" in fleet
    assert "complianceMiss" in fleet
    assert "formatPeelMissMessage" in fleet
    assert "miss" in compliance


def test_sdk_health_modules_reject_via_broker_miss() -> None:
    """sak485-i: health/modules reject via=broker_miss."""
    from broker_client.client import BrokerClient

    ts = (
        Path(__file__).resolve().parents[3]
        / "SwissArmyNoife"
        / "sdks"
        / "typescript"
        / "src"
        / "index.ts"
    ).read_text(encoding="utf-8")
    assert "sak485-i" in ts

    py = (
        Path(__file__).resolve().parents[3]
        / "SwissArmyNoife"
        / "sdks"
        / "python"
        / "src"
        / "swissarmynoife"
        / "client.py"
    ).read_text(encoding="utf-8")
    assert "sak485-i" in py

    client = BrokerClient(base_url="http://example.test", client=MagicMock())
    miss = {"via": "broker_miss", "status": "degraded", "feature": "health"}
    with patch("broker_client.client.get_json", return_value=miss):
        with pytest.raises(RuntimeError, match="broker_miss"):
            client.health()
        with pytest.raises(RuntimeError, match="broker_miss"):
            client.list_modules()

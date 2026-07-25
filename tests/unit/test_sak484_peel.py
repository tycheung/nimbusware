from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def _js_root() -> Path:
    return Path(__file__).resolve().parents[2] / "packages" / "maker_web" / "static" / "js"


def test_home_session_hub_miss() -> None:
    """sak484-a."""
    root = _js_root()
    home = (root / "tabs" / "home.js").read_text(encoding="utf-8")
    hub = (root / "session-hub.js").read_text(encoding="utf-8")
    assert "toastIfMiss" in home
    assert "Factory analytics unavailable" in home
    assert "toastIfMiss" in hub


def test_chat_shell_session_miss() -> None:
    """sak484-b."""
    tabs = _js_root() / "tabs"
    chat = (tabs / "chat.js").read_text(encoding="utf-8")
    lifecycle = (tabs / "chat_session_lifecycle.js").read_text(encoding="utf-8")
    session = (tabs / "chat_session_ui.js").read_text(encoding="utf-8")
    assert "toastIfMiss" in chat or "isBrokerMiss" in chat
    assert "isBrokerMiss" in lifecycle or "toastIfMiss" in lifecycle
    assert "isBrokerMiss" in session


def test_library_discovery_composer_miss() -> None:
    """sak484-c."""
    tabs = _js_root() / "tabs"
    library = (tabs / "chat_library_ui.js").read_text(encoding="utf-8")
    discovery = (tabs / "chat_discovery_ui.js").read_text(encoding="utf-8")
    composer = (tabs / "chat_composer_ui.js").read_text(encoding="utf-8")
    assert "missBannerText" in library or "toastIfMiss" in library
    assert "toastIfMiss" in discovery
    assert "toastIfMiss" in composer


def test_settings_review_build_wizard_miss() -> None:
    """sak484-d."""
    root = _js_root()
    tabs = root / "tabs"
    optimizer = (tabs / "settings_optimizer_ui.js").read_text(encoding="utf-8")
    memory = (tabs / "settings_memory_stitch_ui.js").read_text(encoding="utf-8")
    review = (tabs / "review_git_ui.js").read_text(encoding="utf-8")
    build = (tabs / "build.js").read_text(encoding="utf-8")
    wizard = (tabs / "wizard.js").read_text(encoding="utf-8")
    archetype = (root / "archetype-picker.js").read_text(encoding="utf-8")
    assert "toast(" in optimizer
    assert "toastIfMiss" in memory
    assert "toastIfMiss" in review or "missBannerText" in review
    assert "toastIfMiss" in build
    assert "toastIfMiss" in wizard
    assert "toastIfMiss" in archetype


def test_campaign_openapi() -> None:
    """sak484-e."""
    from api.routes.campaigns.create import CreateCampaignResponse
    from api.routes.campaigns.lifecycle import CampaignActionResponse
    from api.routes.campaigns.progress import CampaignProgressResponse

    assert CreateCampaignResponse().via is None
    assert CampaignProgressResponse().via is None
    assert CampaignActionResponse().via is None


def test_artifact_push_integrations_openapi() -> None:
    """sak484-f."""
    from api.routes.integrations import ExternalChatCapabilitiesResponse
    from api.routes.maker_push import PushSubscriptionListResponse
    from api.routes.runs.artifact_bundle import CampaignArtifactBundleResponse

    assert CampaignArtifactBundleResponse().via is None
    assert PushSubscriptionListResponse().via is None
    assert ExternalChatCapabilitiesResponse().via is None


def test_chat_timeline_explain_openapi() -> None:
    """sak484-g."""
    from api.routes.chat_common import ChatSessionListResponse, ChatSessionResponse
    from api.routes.runs.timeline_explain import TimelineExplainResponse

    assert ChatSessionListResponse(sessions=[]).sessions == []
    assert (
        ChatSessionResponse(
            session_id="s1",
            project_id="p1",
            created_at="2026-01-01T00:00:00Z",
            messages=[],
        ).via
        is None
    )
    assert TimelineExplainResponse().via is None


def test_admin_run_detail_panels_peel() -> None:
    """sak484-h."""
    root = Path(__file__).resolve().parents[2] / "packages" / "admin_ui" / "src"
    timeline = (root / "components" / "TimelineAccordion.tsx").read_text(encoding="utf-8")
    theater = (root / "components" / "TheaterPanel.tsx").read_text(encoding="utf-8")
    launch = (root / "components" / "LaunchScorecardPanel.tsx").read_text(encoding="utf-8")
    bundle = (root / "components" / "BundleOutcomePanel.tsx").read_text(encoding="utf-8")
    campaign = (root / "context" / "CampaignProgressContext.tsx").read_text(encoding="utf-8")
    assert "formatPeelMissMessage" in timeline
    assert "isComputeMiss" in timeline
    assert "formatPeelMissMessage" in theater
    assert "formatPeelMissMessage" in launch
    assert "formatPeelMissMessage" in bundle
    assert "formatPeelMissMessage" in campaign
    assert "_Explain unavailable._" not in timeline


def test_sdk_node_path_rejects_via_broker_miss() -> None:
    """sak484-i: node-path helpers reject via=broker_miss."""
    from broker_client.client import BrokerClient

    ts = (
        Path(__file__).resolve().parents[3]
        / "SwissArmyNoife"
        / "sdks"
        / "typescript"
        / "src"
        / "index.ts"
    ).read_text(encoding="utf-8")
    assert "sak484-i" in ts

    py = (
        Path(__file__).resolve().parents[3]
        / "SwissArmyNoife"
        / "sdks"
        / "python"
        / "src"
        / "swissarmynoife"
        / "client.py"
    ).read_text(encoding="utf-8")
    assert "sak484-i" in py

    client = BrokerClient(base_url="http://example.test", client=MagicMock())
    miss = {"via": "broker_miss", "status": "degraded", "feature": "register_node"}
    with patch.object(client, "compute_nodes", return_value=miss):
        with pytest.raises(RuntimeError, match="broker_miss"):
            client.register_node("worker-a", node_id="n1")
        with pytest.raises(RuntimeError, match="broker_miss"):
            client.heartbeat_node(node_id="n1")

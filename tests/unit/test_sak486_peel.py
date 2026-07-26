from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def _js_root() -> Path:
    return Path(__file__).resolve().parents[2] / "packages" / "maker_web" / "static" / "js"


def test_chat_popover_work_type_miss() -> None:
    """sak486-a."""
    tabs = _js_root() / "tabs"
    popover = (tabs / "chat_agent_popover_ui.js").read_text(encoding="utf-8")
    work = (tabs / "chat_work_type.js").read_text(encoding="utf-8")
    assert "toastIfMiss" in popover
    assert "toastIfMiss" in work


def test_progress_sse_enrich_miss() -> None:
    """sak486-b."""
    progress = (_js_root() / "tabs" / "progress.js").read_text(encoding="utf-8")
    assert "renderProgressMiss" in progress
    assert "handleEnrichFailure" in progress


def test_context_run_card_residual_miss() -> None:
    """sak486-c."""
    root = _js_root()
    context = (root / "tabs" / "progress" / "context-panels.js").read_text(encoding="utf-8")
    card = (root / "tabs" / "chat_run_card_ui.js").read_text(encoding="utf-8")
    assert "maker-context-artifact-miss" in context
    assert "broker_miss" in card
    assert "toastIfMiss" in card or "isBrokerMiss" in card


def test_settings_models_write_path_miss() -> None:
    """sak486-d."""
    root = _js_root()
    connections = (root / "tabs" / "models_connections_ui.js").read_text(encoding="utf-8")
    governor = (root / "tabs" / "settings_governor_ui.js").read_text(encoding="utf-8")
    compact = (root / "tabs" / "progress" / "compact-toolbar.js").read_text(encoding="utf-8")
    assert "toastIfMiss" in connections
    assert "toastIfMiss" in governor
    assert "toastIfMiss" in compact


def test_enterprise_research_openapi() -> None:
    """sak486-e."""
    from api.routes.enterprise.config_notify import ConfigNotifyStatusResponse
    from api.routes.enterprise.object_store import ScraperArtifactStorageResponse
    from api.routes.enterprise.research_ops import ResearchIndexResponse
    from api.routes.enterprise.users import EnterpriseUserSearchResponse

    assert ResearchIndexResponse().via is None
    assert ScraperArtifactStorageResponse().via is None
    assert ConfigNotifyStatusResponse().via is None
    assert EnterpriseUserSearchResponse().via is None


def test_model_collab_policy_openapi() -> None:
    """sak486-f."""
    from api.routes.enterprise.collab_policy import CollabPolicyResponse
    from api.routes.enterprise.model_policy import ModelPolicyResponse

    assert ModelPolicyResponse().via is None
    assert CollabPolicyResponse().via is None


def test_runs_lifecycle_openapi() -> None:
    """sak486-g."""
    from api.routes.runs.context_artifacts import ContextArtifactInsertResponse
    from api.routes.runs.lifecycle import LifecycleStartResponse
    from api.routes.runs.research import ResearchApproveResponse

    assert ContextArtifactInsertResponse().via is None
    assert LifecycleStartResponse().via is None
    assert ResearchApproveResponse().via is None


def test_config_metrics_write_peel() -> None:
    """sak486-h / sak486-i admin."""
    root = Path(__file__).resolve().parents[2] / "packages" / "admin_ui" / "src"
    peel = (root / "api" / "peel_assert.ts").read_text(encoding="utf-8")
    config = (root / "pages" / "ConfigPage.tsx").read_text(encoding="utf-8")
    metrics = (root / "pages" / "MetricsPage.tsx").read_text(encoding="utf-8")
    assert "writeMissMessage" in peel
    assert "assertWriteOk" in peel
    assert "writeMissMessage" in config or "formatWriteCatchMessage" in config
    assert "competitive metrics unavailable" in metrics
    assert "isDomainPeelMiss" in metrics


def test_sdk_capacity_assert_rejects_via_broker_miss() -> None:
    """sak486-i: health/capacity use assert_capacity_ok."""
    from broker_client.client import BrokerClient

    ts = (
        Path(__file__).resolve().parents[3]
        / "SwissArmyNoife"
        / "sdks"
        / "typescript"
        / "src"
        / "index.ts"
    ).read_text(encoding="utf-8")
    assert "sak486-i" in ts

    py = (
        Path(__file__).resolve().parents[3]
        / "SwissArmyNoife"
        / "sdks"
        / "python"
        / "src"
        / "swissarmynoife"
        / "client.py"
    ).read_text(encoding="utf-8")
    assert "sak486-i" in py

    client = BrokerClient(base_url="http://example.test", client=MagicMock())
    miss = {"via": "broker_miss", "status": "degraded", "feature": "capacity"}
    with patch("broker_client.client.get_json", return_value=miss):
        with pytest.raises(RuntimeError, match="broker_miss"):
            client.health()
        with pytest.raises(RuntimeError, match="broker_miss"):
            client.capacity()

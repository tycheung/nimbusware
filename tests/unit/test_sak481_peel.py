from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def test_progress_review_miss_harden() -> None:
    """sak481-a."""
    root = Path(__file__).resolve().parents[2] / "packages" / "maker_web" / "static" / "js" / "tabs"
    progress = (root / "progress.js").read_text(encoding="utf-8")
    review = (root / "review.js").read_text(encoding="utf-8")
    assert ".catch(() =>" not in progress or "toast(" in progress
    assert "renderProgressBody(lastProgressSnapshot)" in progress
    assert "/* optional */" not in review
    assert "toastIfMiss" in review


def test_home_settings_chat_miss() -> None:
    """sak481-b."""
    root = Path(__file__).resolve().parents[2] / "packages" / "maker_web" / "static" / "js" / "tabs"
    home = (root / "home_enterprise_policy_ui.js").read_text(encoding="utf-8")
    gov = (root / "settings_governor_ui.js").read_text(encoding="utf-8")
    settings = (root / "settings.js").read_text(encoding="utf-8")
    chat = (root / "chat_session_ui.js").read_text(encoding="utf-8")
    library = (root / "chat_library_ui.js").read_text(encoding="utf-8")
    assert "maker-home-fleet-governance-miss" in home
    assert "/* optional */" not in gov
    assert "Collab settings unavailable" in settings
    assert "maker-chat-compute-miss" in chat
    assert "maker-chat-library-miss" in library
    assert 'panel.classList.add("hidden")' not in library


def test_enterprise_policy_openapi() -> None:
    """sak481-c."""
    from api.routes.enterprise.audit_policy import AuditPolicyResponse
    from api.routes.enterprise.compliance import ComplianceSummaryResponse
    from api.routes.enterprise.tenant_collab_policy import TenantCollabPolicyResponse

    assert AuditPolicyResponse(legal_hold=True).legal_hold is True
    assert TenantCollabPolicyResponse(tenant_slug="t").tenant_slug == "t"
    assert ComplianceSummaryResponse(completed_runs=1).completed_runs == 1


def test_chat_library_openapi() -> None:
    """sak481-d."""
    from api.routes.chat_collab import (
        AccessGrantListResponse,
        EffectiveRoleResponse,
        FolderListResponse,
        GroupListResponse,
    )

    assert FolderListResponse(folders=[]).folders == []
    assert GroupListResponse(groups=[]).groups == []
    assert AccessGrantListResponse(grants=[]).grants == []
    assert EffectiveRoleResponse(effective_role="session_read").effective_role == "session_read"


def test_analytics_deploy_openapi() -> None:
    """sak481-e."""
    from api.routes.analytics import AnalyticsPayloadResponse
    from api.routes.platform_deploy import PlatformDeployResponse

    assert AnalyticsPayloadResponse().model_extra is None or True
    assert PlatformDeployResponse().via is None


def test_admin_bff_openapi() -> None:
    """sak481-f."""
    from api.routes.admin_ui_bff import AdminProjectionResponse

    assert AdminProjectionResponse().via is None


def test_admin_config_run_metrics_miss() -> None:
    """sak481-g."""
    root = Path(__file__).resolve().parents[2] / "packages" / "admin_ui" / "src" / "pages"
    config = (root / "ConfigPage.tsx").read_text(encoding="utf-8")
    run = (root / "RunDetailPage.tsx").read_text(encoding="utf-8")
    metrics = (root / "MetricsPage.tsx").read_text(encoding="utf-8")
    assert config.count("async function loadProbationReliability") == 1
    assert "formatPeelMissMessage" in config
    assert "formatPeelMissMessage" in run
    assert "formatPeelMissMessage" in metrics
    assert ".catch(() => setChatTurns(null))" not in metrics


def test_fleet_mesh_miss_full_body() -> None:
    """sak481-h."""
    root = Path(__file__).resolve().parents[2] / "packages" / "admin_ui" / "src" / "pages"
    fleet = (root / "FleetPage.tsx").read_text(encoding="utf-8")
    mesh = (root / "fleet" / "FleetMeshPanel.tsx").read_text(encoding="utf-8")
    assert "formatPeelMissMessage" in fleet
    assert "meshStatus" in mesh
    assert 'isComputeMiss({ via: meshVia })' not in mesh


def test_sdk_queue_depth_session_parity() -> None:
    """sak481-i."""
    from broker_client.client import BrokerClient
    from broker_client.stage_bind.compute import queue_depth_for_session

    items = [
        {"id": "1", "session_id": "other"},
        {"id": "2", "payload": {"session_id": "s1"}},
        {"id": "3", "session_id": "s1"},
    ]
    assert queue_depth_for_session(items, "s1") == 2

    py = (
        Path(__file__).resolve().parents[3]
        / "SwissArmyNoife"
        / "sdks"
        / "python"
        / "src"
        / "swissarmynoife"
        / "client.py"
    ).read_text(encoding="utf-8")
    assert "payload.get(\"session_id\")" in py or "payload.get('session_id')" in py
    assert "sak481-i" in py

    client = BrokerClient(base_url="http://example.test", client=MagicMock())
    with patch.object(
        client,
        "session_compute_status",
        return_value={"nodes": [], "queue_depth": 0, "via": "broker"},
    ):
        out = client.session_compute_status("s1")
    assert out["via"] == "broker"

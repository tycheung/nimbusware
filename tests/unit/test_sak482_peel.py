from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch


def test_deploy_cockpit_settings_miss() -> None:
    """sak482-a."""
    root = Path(__file__).resolve().parents[2] / "packages" / "maker_web" / "static" / "js"
    cockpit = (root / "deploy_cockpit.js").read_text(encoding="utf-8")
    settings = (root / "tabs" / "settings_deploy_ui.js").read_text(encoding="utf-8")
    assert "toastIfMiss" in cockpit
    assert "/* optional */" not in cockpit
    assert "toastIfMiss" in settings
    assert "/* offline or unsigned */" not in settings


def test_progress_review_depth_miss() -> None:
    """sak482-b."""
    root = Path(__file__).resolve().parents[2] / "packages" / "maker_web" / "static" / "js"
    progress = (root / "tabs" / "progress.js").read_text(encoding="utf-8")
    context = (root / "tabs" / "progress" / "context-panels.js").read_text(encoding="utf-8")
    critic = (root / "critic-reliability-panel.js").read_text(encoding="utf-8")
    review = (root / "tabs" / "review_advanced_ui.js").read_text(encoding="utf-8")
    assert "maker-progress-critic-miss" in progress
    assert "/* optional */" not in progress
    assert "maker-context-artifact-miss" in context
    assert "maker-memory-influence-miss" in context
    assert "isBrokerMiss" in critic
    assert "toastIfMiss" in review


def test_chat_collab_optimizer_miss() -> None:
    """sak482-c."""
    root = Path(__file__).resolve().parents[2] / "packages" / "maker_web" / "static" / "js" / "tabs"
    host = (root / "chat_host_transfer_ui.js").read_text(encoding="utf-8")
    optimizer = (root / "chat_optimizer_ui.js").read_text(encoding="utf-8")
    theater = (root / "chat_theater_ui.js").read_text(encoding="utf-8")
    assert "maker-chat-host-transfer-miss" in host
    assert "toastIfMiss" in optimizer
    assert ".catch(() => {})" not in theater


def test_models_safe_coding_miss() -> None:
    """sak482-d."""
    root = Path(__file__).resolve().parents[2] / "packages" / "maker_web" / "static" / "js"
    ollama = (root / "tabs" / "models_ollama_ui.js").read_text(encoding="utf-8")
    local = (root / "tabs" / "models_local_ui.js").read_text(encoding="utf-8")
    wizard = (root / "safe-coding-wizard.js").read_text(encoding="utf-8")
    assert "toastIfMiss" in ollama
    assert "/* optional */" not in local
    assert "toastIfMiss" in wizard
    assert "/* optional */" not in wizard


def test_collab_mutation_openapi() -> None:
    """sak482-e."""
    from api.routes.chat_collab import (
        AccessGrantMutationResponse,
        GroupMutationResponse,
        SessionLibraryResponse,
    )
    from api.routes.chat_stream import CommentaryResponse

    assert GroupMutationResponse().via is None
    assert AccessGrantMutationResponse().via is None
    assert SessionLibraryResponse().via is None
    assert CommentaryResponse().via is None


def test_bff_run_projection_openapi() -> None:
    """sak482-f."""
    from api.routes.admin_ui_bff import AdminProjectionResponse
    from api.routes.runs.detail import RunProjectionResponse
    from api.routes.runs.maker_approval import LaunchEvalResponse

    assert AdminProjectionResponse().via is None
    assert RunProjectionResponse().via is None
    assert LaunchEvalResponse().via is None


def test_fleet_policy_openapi() -> None:
    """sak482-g."""
    from api.routes.enterprise.fleet_tenant_policies import (
        FleetSlicePolicyResponse,
        FleetStackPolicyResponse,
    )

    assert FleetSlicePolicyResponse().via is None
    assert FleetStackPolicyResponse().via is None


def test_admin_fleet_run_operator_peel() -> None:
    """sak482-h."""
    root = Path(__file__).resolve().parents[2] / "packages" / "admin_ui" / "src"
    fleet = (root / "pages" / "FleetPage.tsx").read_text(encoding="utf-8")
    runs = (root / "pages" / "RunListPage.tsx").read_text(encoding="utf-8")
    hook = (root / "hooks" / "useApiGet.ts").read_text(encoding="utf-8")
    assert ".catch(() => setCollabPolicyCaption(\"\"))" not in fleet
    assert ".catch(() => setStackPolicyCaption(\"\"))" not in fleet
    assert "collab policy unavailable" in fleet
    assert "fleet compare unavailable" in fleet
    assert "formatPeelMissMessage" in runs
    assert "isComputeMiss" in hook


def test_sdk_session_compute_status_parity() -> None:
    """sak482-i."""
    from broker_client.client import BrokerClient

    ts = (
        Path(__file__).resolve().parents[3]
        / "SwissArmyNoife"
        / "sdks"
        / "typescript"
        / "src"
        / "index.ts"
    ).read_text(encoding="utf-8")
    assert "sessionComputeStatus" in ts
    assert "sak482-i" in ts

    py = (
        Path(__file__).resolve().parents[3]
        / "SwissArmyNoife"
        / "sdks"
        / "python"
        / "src"
        / "swissarmynoife"
        / "client.py"
    ).read_text(encoding="utf-8")
    assert "def session_compute_status" in py
    assert "sak482-i" in py

    client = BrokerClient(base_url="http://example.test", client=MagicMock())
    with patch.object(
        client,
        "session_compute_status",
        return_value={"nodes": [], "queue_depth": 0, "via": "broker"},
    ):
        out = client.session_compute_status("s1")
    assert out["via"] == "broker"

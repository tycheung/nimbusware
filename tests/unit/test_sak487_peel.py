from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def _js_root() -> Path:
    return Path(__file__).resolve().parents[2] / "packages" / "maker_web" / "static" / "js"


def test_chat_agents_model_drawer_write_miss() -> None:
    """sak487-a."""
    tabs = _js_root() / "tabs"
    agents = (tabs / "chat_agents_ui.js").read_text(encoding="utf-8")
    drawer = (tabs / "chat_model_drawer_ui.js").read_text(encoding="utf-8")
    assert "Role claim unavailable" in agents or "toastIfMiss" in agents
    assert "Model swap unavailable" in agents
    assert "toastIfMiss" in drawer


def test_review_write_miss() -> None:
    """sak487-b."""
    tabs = _js_root() / "tabs"
    review = (tabs / "review.js").read_text(encoding="utf-8")
    git = (tabs / "review_git_ui.js").read_text(encoding="utf-8")
    assert "toastIfMiss" in review
    assert "toastIfMiss" in git


def test_home_settings_write_miss() -> None:
    """sak487-c."""
    tabs = _js_root() / "tabs"
    home = (tabs / "home.js").read_text(encoding="utf-8")
    settings = (tabs / "settings.js").read_text(encoding="utf-8")
    assert "toastIfMiss" in home
    assert "toastIfMiss" in settings


def test_memory_stitch_write_miss() -> None:
    """sak487-d."""
    stitch = (_js_root() / "tabs" / "settings_memory_stitch_ui.js").read_text(
        encoding="utf-8"
    )
    assert "toastIfMiss" in stitch
    assert "promote" in stitch.lower() or "memory-chunk" in stitch


def test_actions_runs_openapi() -> None:
    """sak487-e."""
    from api.routes.actions import ActionStatusResponse, RoleExecuteResponse
    from api.routes.runs.create import CreateRunResponse
    from api.routes.runs.memory_insert import MemoryChunkInsertResponse

    assert ActionStatusResponse().via is None
    assert RoleExecuteResponse().via is None
    assert CreateRunResponse().via is None
    assert MemoryChunkInsertResponse().via is None


def test_personas_bundles_critics_openapi() -> None:
    """sak487-f."""
    from api.routes.bundles import BundleCatalogSourceResponse
    from api.routes.config_ops import ConfigBlastRadiusResponse
    from api.routes.critic_packs import CriticPackListResponse
    from api.routes.personas_handlers import PersonaOverlapReportResponse

    assert PersonaOverlapReportResponse().via is None
    assert BundleCatalogSourceResponse().via is None
    assert ConfigBlastRadiusResponse().via is None
    assert CriticPackListResponse().via is None


def test_ollama_auth_openapi() -> None:
    """sak487-g."""
    from api.routes.admin_oauth import AdminOAuthSessionResponse
    from api.routes.auth import SignoutResponse
    from api.schemas.ollama import OllamaModelsResponse

    assert SignoutResponse().via is None
    assert AdminOAuthSessionResponse().via is None
    assert "via" in OllamaModelsResponse.model_fields
    assert "error" in OllamaModelsResponse.model_fields
    assert "feature" in OllamaModelsResponse.model_fields


def test_admin_rundetail_login_peel() -> None:
    """sak487-h."""
    root = Path(__file__).resolve().parents[2] / "packages" / "admin_ui" / "src"
    run = (root / "pages" / "RunDetailPage.tsx").read_text(encoding="utf-8")
    research = (root / "components" / "ResearchPanel.tsx").read_text(encoding="utf-8")
    login = (root / "LoginGate.tsx").read_text(encoding="utf-8")
    assert "writeMissMessage" in run
    assert "formatWriteCatchMessage" in run
    assert "writeMissMessage" in research or "formatWriteCatchMessage" in research
    assert "oidcMiss" in login
    assert "SSO session unavailable" in login


def test_sdk_assert_record_ok_rejects_via_broker_miss() -> None:
    """sak487-i: write-path assert_record_ok rejects via=broker_miss."""
    from compute.broker_session_status import assert_broker_compute_record_ok

    ts = (
        Path(__file__).resolve().parents[3]
        / "SwissArmyNoife"
        / "sdks"
        / "typescript"
        / "src"
        / "index.ts"
    ).read_text(encoding="utf-8")
    assert "sak487-i" in ts

    py = (
        Path(__file__).resolve().parents[3]
        / "SwissArmyNoife"
        / "sdks"
        / "python"
        / "src"
        / "swissarmynoife"
        / "client.py"
    ).read_text(encoding="utf-8")
    assert "sak487-i" in py

    miss = {"via": "broker_miss", "status": "degraded", "feature": "enqueue"}
    with pytest.raises(RuntimeError, match="broker_miss"):
        assert_broker_compute_record_ok(miss, feature="test", record_key="work")

    client_src = (
        Path(__file__).resolve().parents[2]
        / "packages"
        / "broker_client"
        / "client.py"
    ).read_text(encoding="utf-8")
    assert "sak487-i" in client_src

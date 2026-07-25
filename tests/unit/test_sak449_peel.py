from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def test_review_git_no_empty_masquerade() -> None:
    """sak449-a."""
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
    assert ".catch(() => ({}))" not in text
    assert ".catch(() => ({ events: [] }))" not in text
    assert 'via: "broker_miss"' in text
    assert "toastIfMiss" in text


def test_plan_and_run_card_timeline_miss() -> None:
    """sak449-b."""
    root = Path(__file__).resolve().parents[2] / "packages" / "maker_web" / "static" / "js" / "tabs"
    plan = (root / "plan.js").read_text(encoding="utf-8")
    card = (root / "chat_run_card_ui.js").read_text(encoding="utf-8")
    assert ".catch(() => ({ events: [] }))" not in plan
    assert ".catch(() => null)" not in plan
    assert 'via: "broker_miss"' in plan
    assert ".catch(() => ({ events: [] }))" not in card
    assert "toastIfMiss" in card


def test_stitch_catalog_no_fake_version() -> None:
    """sak449-c."""
    root = Path(__file__).resolve().parents[2] / "packages" / "maker_web" / "static" / "js" / "tabs"
    stitch = (root / "settings_memory_stitch_ui.js").read_text(encoding="utf-8")
    ribbon = (root / "progress" / "integrator-ribbon.js").read_text(encoding="utf-8")
    assert ".catch(() => ({ document_version: 1 }))" not in stitch
    assert ".catch(() => ({ document_version: 1 }))" not in ribbon
    assert "toastIfMiss" in stitch
    assert "toastIfMiss" in ribbon


def test_platform_collab_edition_openapi() -> None:
    """sak449-d."""
    from api.routes.platform import (
        CollabSettingsResponse,
        PlatformEditionResponse,
        PlaywrightBootstrapResponse,
    )

    assert CollabSettingsResponse(collab_enabled=True).collab_enabled is True
    assert PlatformEditionResponse(edition="individual").edition == "individual"
    assert PlaywrightBootstrapResponse(status="ready").status == "ready"


def test_enterprise_core_commit_openapi() -> None:
    """sak449-e."""
    from api.routes.enterprise.core import EnterpriseHealthResponse, EnterpriseStatusResponse
    from api.routes.enterprise.fleet_commit import FleetCommitPolicyResponse

    assert EnterpriseStatusResponse(edition="enterprise").edition == "enterprise"
    assert EnterpriseHealthResponse(ok=True).ok is True
    assert FleetCommitPolicyResponse(require_auto_commit=True).require_auto_commit is True


def test_host_transfer_openapi() -> None:
    """sak449-f."""
    from api.routes.chat_collab import HostTransferListResponse, HostTransferResponse

    assert HostTransferResponse(ok=True).ok is True
    assert HostTransferListResponse(transfers=[]).transfers == []


def test_admin_is_compute_miss() -> None:
    """sak449-g."""
    root = Path(__file__).resolve().parents[2] / "packages" / "admin_ui" / "src"
    peel = (root / "api" / "peel_assert.ts").read_text(encoding="utf-8")
    fleet = (root / "pages" / "FleetPage.tsx").read_text(encoding="utf-8")
    mesh = (root / "pages" / "fleet" / "FleetMeshPanel.tsx").read_text(encoding="utf-8")
    assert "export function isComputeMiss" in peel
    assert "isComputeMiss" in fleet
    assert "isComputeMiss" in mesh
    assert ".catch(() => ({ hits: [], embedding_mode: \"none\" }))" not in fleet


def test_admin_normalize_compute_action_miss() -> None:
    """sak449-h."""
    api = Path(__file__).resolve().parents[2] / "packages" / "admin_ui" / "src" / "api"
    peel = (api / "peel_assert.ts").read_text(encoding="utf-8")
    client = (api / "client.ts").read_text(encoding="utf-8")
    assert "export function normalizeComputeActionMiss" in peel
    assert "normalizeComputeActionMiss" in client
    assert "raw.via === \"broker_miss\" || raw.error != null" not in client


def test_broker_client_and_sdk_health_assert() -> None:
    """sak449-i."""
    from broker_client.client import BrokerClient

    client = BrokerClient(base_url="http://example.test", client=MagicMock())
    with patch(
        "broker_client.client.get_json",
        return_value={"error": "down"},
    ):
        with pytest.raises(RuntimeError, match="broker_miss"):
            client.get_module("x")
        with pytest.raises(RuntimeError, match="broker_miss"):
            client.capacity()

    py = (
        Path(__file__).resolve().parents[3]
        / "SwissArmyNoife"
        / "sdks"
        / "python"
        / "src"
        / "swissarmynoife"
        / "client.py"
    ).read_text(encoding="utf-8")
    assert 'feature="health"' in py
    ts = (
        Path(__file__).resolve().parents[3]
        / "SwissArmyNoife"
        / "sdks"
        / "typescript"
        / "src"
        / "index.ts"
    ).read_text(encoding="utf-8")
    assert "assertCapacityOk(await this.getJson(\"/health\"))" in ts
    rust = (
        Path(__file__).resolve().parents[3]
        / "SwissArmyNoife"
        / "crates"
        / "sdk"
        / "src"
        / "client.rs"
    ).read_text(encoding="utf-8")
    assert "assert_capacity_ok(&raw)" in rust
    assert "sak449-i" in rust

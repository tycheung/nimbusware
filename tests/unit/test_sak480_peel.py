from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def test_progress_ribbon_and_settings_catalog_miss() -> None:
    """sak480-a."""
    root = Path(__file__).resolve().parents[2] / "packages" / "maker_web" / "static" / "js" / "tabs"
    ribbon = (root / "progress" / "progress_ribbon_refresh.js").read_text(encoding="utf-8")
    settings = (root / "settings.js").read_text(encoding="utf-8")
    plan = (root / "plan.js").read_text(encoding="utf-8")
    review = (root / "review.js").read_text(encoding="utf-8")
    assert ".catch(() => null)" not in ribbon
    assert 'via: "broker_miss"' in ribbon
    assert ".catch(() => null)" not in settings
    assert "toastIfMiss" in settings
    assert ".catch(() => {})" not in plan
    assert ".catch(() => {})" not in review


def test_safe_coding_integrator_completion_miss() -> None:
    """sak480-b."""
    root = Path(__file__).resolve().parents[2] / "packages" / "maker_web" / "static" / "js" / "tabs"
    safe = (root / "settings_safe_coding_ui.js").read_text(encoding="utf-8")
    integ = (root / "progress" / "integrator-ribbon.js").read_text(encoding="utf-8")
    chips = (root / "progress" / "render-chips.js").read_text(encoding="utf-8")
    assert "toastIfMiss" in safe
    assert "/* optional */" not in safe
    assert 'via: "broker_miss"' in integ
    assert "toastIfMiss" in chips


def test_operator_settings_openapi() -> None:
    """sak480-c."""
    from api.routes.operator_settings import SettingsCatalogResponse, SettingsScopeResponse

    assert SettingsCatalogResponse().install == {}
    assert SettingsScopeResponse(values={"a": "1"}).values == {"a": "1"}


def test_platform_safe_coding_scaffold_openapi() -> None:
    """sak480-d."""
    from api.routes.platform import (
        IndustryCriticPacksResponse,
        SafeCodingPreferencesResponse,
        WorkspaceScaffoldResponse,
    )

    assert IndustryCriticPacksResponse(packs=[]).packs == []
    assert SafeCodingPreferencesResponse(user_id="u").user_id == "u"
    assert WorkspaceScaffoldResponse(created=[]).created == []


def test_memory_fleet_dashboard_openapi() -> None:
    """sak480-e."""
    from api.routes.admin_ui_bff import FleetDashboardResponse
    from api.routes.bundles import CatalogCandidatesResponse
    from api.routes.enterprise.fleet_memory import (
        FleetMemorySearchResponse,
        FleetMemoryStatusResponse,
    )
    from api.routes.memory_chunks import MemoryChunksResponse

    assert MemoryChunksResponse(total=0).total == 0
    assert FleetMemoryStatusResponse(local_chunk_count=0).local_chunk_count == 0
    assert FleetMemorySearchResponse(hits=[]).hits == []
    assert CatalogCandidatesResponse(candidates=[]).candidates == []
    assert FleetDashboardResponse().hardware_rows == []


def test_host_transfer_lifecycle_openapi() -> None:
    """sak480-f."""
    from api.routes.chat_collab import HostTransferBundleResponse, HostTransferResponse

    assert HostTransferBundleResponse(manifest={}).manifest == {}
    assert HostTransferResponse(ok=True).ok is True


def test_admin_is_memory_miss_helpers() -> None:
    """sak480-g."""
    root = Path(__file__).resolve().parents[2] / "packages" / "admin_ui" / "src"
    peel = (root / "api" / "peel_assert.ts").read_text(encoding="utf-8")
    fleet = (root / "pages" / "FleetPage.tsx").read_text(encoding="utf-8")
    assert "export function isMemoryMiss" in peel
    assert "export function formatPeelMissMessage" in peel
    assert "isMemoryMiss" in fleet
    assert "hits: [] as FleetCombinedSearch" not in fleet
    assert "return status;" not in fleet or "status: \"degraded\"" in fleet


def test_admin_format_capacity_miss() -> None:
    """sak480-h."""
    root = Path(__file__).resolve().parents[2] / "packages" / "admin_ui" / "src"
    peel = (root / "api" / "peel_assert.ts").read_text(encoding="utf-8")
    hw = (root / "pages" / "HardwarePage.tsx").read_text(encoding="utf-8")
    fleet = (root / "pages" / "FleetPage.tsx").read_text(encoding="utf-8")
    assert "export function formatCapacityMissMessage" in peel
    assert "formatCapacityMissMessage" in hw
    assert "formatCapacityMissMessage" in fleet


def test_sdk_queue_depth_and_terminate() -> None:
    """sak480-i."""
    from broker_client.client import BrokerClient

    src = (
        Path(__file__).resolve().parents[2] / "packages" / "broker_client" / "client.py"
    ).read_text(encoding="utf-8")
    assert "build_compute_list_payload" not in src.split("def queue_depth")[1].split("def ")[0]

    py = (
        Path(__file__).resolve().parents[3]
        / "SwissArmyNoife"
        / "sdks"
        / "python"
        / "src"
        / "swissarmynoife"
        / "client.py"
    ).read_text(encoding="utf-8")
    assert "def terminate_restart_work" in py
    assert "def queue_depth" in py

    ts = (
        Path(__file__).resolve().parents[3]
        / "SwissArmyNoife"
        / "sdks"
        / "typescript"
        / "src"
        / "index.ts"
    ).read_text(encoding="utf-8")
    assert "async queueDepth" in ts
    assert "sak480-i" in ts

    rust = (
        Path(__file__).resolve().parents[3]
        / "SwissArmyNoife"
        / "crates"
        / "sdk"
        / "src"
        / "client.rs"
    ).read_text(encoding="utf-8")
    assert "fn terminate_restart_work" in rust
    assert "fn queue_depth" in rust

    client = BrokerClient(base_url="http://example.test", client=MagicMock())
    with patch.object(
        client,
        "list_work_filtered",
        return_value={"work": [{"id": "1"}, {"id": "2", "session_id": "s1"}]},
    ):
        out = client.queue_depth("s1")
    assert out["queued"] == 1
    assert out["via"] == "broker"

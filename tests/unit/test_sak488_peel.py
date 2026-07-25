from __future__ import annotations

from pathlib import Path

import pytest


def _js_root() -> Path:
    return Path(__file__).resolve().parents[2] / "packages" / "maker_web" / "static" / "js"


def test_run_card_timeline_read_miss() -> None:
    """sak488-a."""
    card = (_js_root() / "tabs" / "chat_run_card_ui.js").read_text(encoding="utf-8")
    assert "maker-chat-timeline-miss" in card
    assert "ensureTimelineMissBanner" in card or "clearTimelineMissBanner" in card


def test_safe_coding_wizard_catch_miss() -> None:
    """sak488-b."""
    wizard = (_js_root() / "safe-coding-wizard.js").read_text(encoding="utf-8")
    assert "toastIfMiss" in wizard
    assert "missBannerText" in wizard


def test_critic_accessible_compute_read_miss() -> None:
    """sak488-c."""
    critic = (_js_root() / "critic-reliability-panel.js").read_text(encoding="utf-8")
    accessible = (_js_root() / "tabs" / "accessible_compute_ui.js").read_text(
        encoding="utf-8"
    )
    assert "toastIfMiss" in critic
    assert "toastIfMiss" in accessible


def test_delete_ok_openapi() -> None:
    """sak488-d."""
    from api.schemas.peel_responses import DeleteOkResponse

    assert DeleteOkResponse().ok is True
    assert DeleteOkResponse().via is None

    projects = (
        Path(__file__).resolve().parents[2]
        / "packages"
        / "api"
        / "routes"
        / "projects.py"
    ).read_text(encoding="utf-8")
    assert "DeleteOkResponse" in projects
    assert "status_code=204" not in projects or "DeleteOkResponse" in projects

    admin = (
        Path(__file__).resolve().parents[2]
        / "packages"
        / "admin_ui"
        / "src"
        / "pages"
        / "ProjectsPage.tsx"
    ).read_text(encoding="utf-8")
    assert "writeMissMessage" in admin


def test_export_peel_json_miss() -> None:
    """sak488-e."""
    from api.export_peel import early_export_json_miss

    assert callable(early_export_json_miss)
    factory = (
        Path(__file__).resolve().parents[2]
        / "packages"
        / "api"
        / "routes"
        / "runs"
        / "factory_evidence.py"
    ).read_text(encoding="utf-8")
    assert "early_export_json_miss" in factory


def test_fleet_hardware_write_peel() -> None:
    """sak488-f / sak488-g."""
    root = Path(__file__).resolve().parents[2] / "packages" / "admin_ui" / "src"
    fleet = (root / "pages" / "FleetPage.tsx").read_text(encoding="utf-8")
    hardware = (root / "pages" / "HardwarePage.tsx").read_text(encoding="utf-8")
    assert "writeMissMessage" in fleet
    assert "formatWriteCatchMessage" in fleet
    assert "formatWriteCatchMessage" in hardware or "writeMissMessage" in hardware


def test_write_miss_message_capacity() -> None:
    """sak488-h."""
    peel = (
        Path(__file__).resolve().parents[2]
        / "packages"
        / "admin_ui"
        / "src"
        / "api"
        / "peel_assert.ts"
    ).read_text(encoding="utf-8")
    assert "isCapacityMiss" in peel
    assert "writeMissMessage" in peel
    assert "formatCapacityMissMessage" in peel

    standards = (
        Path(__file__).resolve().parents[2]
        / "packages"
        / "admin_ui"
        / "src"
        / "pages"
        / "StandardsMartPage.tsx"
    ).read_text(encoding="utf-8")
    assert "writeMissMessage" in standards or "formatWriteCatchMessage" in standards


def test_claim_list_empty_vs_miss() -> None:
    """sak488-i."""
    from compute.broker_session_status import (
        assert_broker_compute_ok,
        normalize_claim_work_response,
    )

    soft = normalize_claim_work_response(
        {"work": None, "error": "queue empty"},
        feature="claim",
    )
    assert soft.get("via") == "broker" or soft.get("work") is None

    with pytest.raises(RuntimeError, match="broker_miss"):
        normalize_claim_work_response(
            {"via": "broker_miss", "error": "queue empty"},
            feature="claim",
        )

    out = assert_broker_compute_ok({"work": []}, feature="list", list_key="work")
    assert out["work"] == []
    with pytest.raises(RuntimeError, match="broker_miss"):
        assert_broker_compute_ok(
            {"via": "broker_miss", "work": []},
            feature="list",
            list_key="work",
        )

    ts = (
        Path(__file__).resolve().parents[3]
        / "SwissArmyNoife"
        / "sdks"
        / "typescript"
        / "src"
        / "index.ts"
    ).read_text(encoding="utf-8")
    assert "sak488-i" in ts

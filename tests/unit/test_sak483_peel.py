from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def _js_root() -> Path:
    return Path(__file__).resolve().parents[2] / "packages" / "maker_web" / "static" / "js"


def test_standards_enforcement_ribbon_miss() -> None:
    """sak483-a."""
    root = _js_root()
    shared = (root / "ribbon-shared.js").read_text(encoding="utf-8")
    standards = (root / "standards-ribbon.js").read_text(encoding="utf-8")
    enforcement = (root / "enforcement-ribbon.js").read_text(encoding="utf-8")
    assert "toastIfMiss" in shared
    assert "registry optional" not in standards
    assert "toastIfMiss" in standards
    assert "toastIfMiss" in enforcement
    assert "catch {" not in enforcement or "toast(" in enforcement


def test_autopilot_interjection_miss() -> None:
    """sak483-b."""
    root = _js_root()
    autopilot = (root / "autopilot-ribbon.js").read_text(encoding="utf-8")
    interjection = (root / "interjection-ribbon.js").read_text(encoding="utf-8")
    assert "toastIfMiss" in autopilot
    assert "toastIfMiss" in interjection
    assert "catch {" not in interjection or "toast(" in interjection


def test_progress_ribbon_gates_miss() -> None:
    """sak483-c."""
    root = _js_root() / "tabs" / "progress"
    refresh = (root / "progress_ribbon_refresh.js").read_text(encoding="utf-8")
    gates = (root / "findings-gates.js").read_text(encoding="utf-8")
    compact = (root / "compact-toolbar.js").read_text(encoding="utf-8")
    assert "toastIfMiss" in refresh or "isDomainPeelMiss" in refresh
    assert "toastIfMiss" in gates
    assert "toastIfMiss" in compact
    assert "catch {" not in gates or "toast(" in gates


def test_chat_shell_residual_miss() -> None:
    """sak483-d."""
    root = _js_root()
    tabs = root / "tabs"
    escalation = (tabs / "chat_escalation_ui.js").read_text(encoding="utf-8")
    chat = (tabs / "chat.js").read_text(encoding="utf-8")
    invite = (tabs / "chat_invite_modal_ui.js").read_text(encoding="utf-8")
    join = (tabs / "chat_join.js").read_text(encoding="utf-8")
    shell = (root / "app-shell.js").read_text(encoding="utf-8")
    assert "catch {}" not in escalation
    assert "fresh session on send" not in chat
    assert "toastIfMiss" in invite
    assert "preview optional" not in join
    assert "hydrateActiveRun(apiJson).catch(() => {})" not in shell


def test_standards_profiles_openapi() -> None:
    """sak483-e."""
    from api.routes.platform_user_profiles import (
        AutopilotPresetResponse,
        EnforcementPresetResponse,
    )
    from api.routes.standards import StandardsRegistryResponse

    assert StandardsRegistryResponse().via is None
    assert AutopilotPresetResponse().via is None
    assert EnforcementPresetResponse().via is None


def test_fleet_tenant_policy_openapi() -> None:
    """sak483-f."""
    from api.routes.enterprise.fleet_autopilot import FleetAutopilotPolicyResponse
    from api.routes.enterprise.fleet_enforcement import FleetEnforcementPolicyResponse
    from api.routes.enterprise.fleet_standards import FleetStandardsPolicyResponse
    from api.routes.enterprise.tenant_model_policy import TenantModelPolicyResponse

    assert FleetEnforcementPolicyResponse().via is None
    assert FleetStandardsPolicyResponse().via is None
    assert FleetAutopilotPolicyResponse().via is None
    assert TenantModelPolicyResponse().via is None


def test_maker_bootstrap_openapi() -> None:
    """sak483-g."""
    from api.routes.enterprise.fleet_memory import FleetMemoryRebuildResponse
    from api.routes.runs.maker_approval import MakerGitStatusResponse
    from api.routes.web_bootstrap import WebBootstrapResponse

    assert MakerGitStatusResponse().via is None
    assert WebBootstrapResponse().via is None
    assert FleetMemoryRebuildResponse().via is None


def test_admin_secondary_pages_peel() -> None:
    """sak483-h."""
    root = Path(__file__).resolve().parents[2] / "packages" / "admin_ui" / "src" / "pages"
    standards = (root / "StandardsMartPage.tsx").read_text(encoding="utf-8")
    projects = (root / "ProjectsPage.tsx").read_text(encoding="utf-8")
    preflight = (root / "PreflightPage.tsx").read_text(encoding="utf-8")
    agents = (root / "CustomAgentsPage.tsx").read_text(encoding="utf-8")
    assert "formatPeelMissMessage" in standards
    assert "isDomainPeelMiss" in standards
    assert "formatPeelMissMessage" in projects
    assert "formatPeelMissMessage" in preflight
    assert "formatPeelMissMessage" in agents


def test_compute_write_path_rejects_via_broker_miss() -> None:
    """sak483-i: write-path helpers reject via=broker_miss without masquerading."""
    from broker_client.client import BrokerClient

    ts = (
        Path(__file__).resolve().parents[3]
        / "SwissArmyNoife"
        / "sdks"
        / "typescript"
        / "src"
        / "index.ts"
    ).read_text(encoding="utf-8")
    assert "isComputeMiss" in ts
    assert "sak483-i" in ts

    py = (
        Path(__file__).resolve().parents[3]
        / "SwissArmyNoife"
        / "sdks"
        / "python"
        / "src"
        / "swissarmynoife"
        / "client.py"
    ).read_text(encoding="utf-8")
    assert "is_compute_miss" in py
    assert "sak483-i" in py

    client = BrokerClient(base_url="http://example.test", client=MagicMock())
    miss = {"via": "broker_miss", "status": "degraded", "feature": "enqueue"}
    with patch("broker_client.client.post_json", return_value=miss):
        with pytest.raises(RuntimeError, match="broker_miss"):
            client.enqueue_work("echo", {"n": 1})
        with pytest.raises(RuntimeError, match="broker_miss"):
            client.get_work("w1")
        with pytest.raises(RuntimeError, match="broker_miss"):
            client.complete_work(work_id="w1", node_id="n1")
        with pytest.raises(RuntimeError, match="broker_miss"):
            client.requeue_work("w1")

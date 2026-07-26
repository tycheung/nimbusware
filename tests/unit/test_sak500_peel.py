from __future__ import annotations

import json
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]


# --- sak500-a: Maker operator ribbons domain peel miss ---


def test_sak500_a_maker_ribbon_domain_peel_miss() -> None:
    """sak500-a: autopilot/enforcement/interjection ribbons drop missBannerText."""
    js = _ROOT / "packages" / "maker_web" / "static" / "js"
    files = (
        js / "autopilot-ribbon.js",
        js / "enforcement-ribbon.js",
        js / "interjection-ribbon.js",
    )
    for path in files:
        src = path.read_text(encoding="utf-8")
        assert "sak500-a" in src, path.name
        assert "missBannerText" not in src, path.name
        assert "isBrokerMiss" not in src, path.name
    enf = (js / "enforcement-ribbon.js").read_text(encoding="utf-8")
    inj = (js / "interjection-ribbon.js").read_text(encoding="utf-8")
    assert "formatDomainMissMessage" in enf
    assert "formatDomainMissMessage" in inj


# --- sak500-b: Maker home enterprise + safe-coding + ribbon-shared ---


def test_sak500_b_maker_enterprise_safe_coding_ribbon_shared() -> None:
    """sak500-b: enterprise/home + safe-coding + ribbon-shared use domain peel helpers."""
    js = _ROOT / "packages" / "maker_web" / "static" / "js"
    enterprise = (js / "tabs" / "home_enterprise_policy_ui.js").read_text(encoding="utf-8")
    wizard = (js / "safe-coding-wizard.js").read_text(encoding="utf-8")
    shared = (js / "ribbon-shared.js").read_text(encoding="utf-8")
    for src, name in (
        (enterprise, "home_enterprise_policy_ui.js"),
        (wizard, "safe-coding-wizard.js"),
        (shared, "ribbon-shared.js"),
    ):
        assert "sak500-b" in src, name
        assert "isBrokerMiss" not in src, name
        assert "missBannerText" not in src, name
    assert "isDomainPeelMiss" in enterprise
    assert "formatDomainMissMessage" in enterprise
    assert "formatDomainMissMessage" in wizard
    assert "isDomainPeelMiss" in shared


# --- sak500-c: admin OperatorChat + StandardsMart + FleetMeshPanel ---


def test_sak500_c_admin_long_tail_domain_peel_miss() -> None:
    """sak500-c: OperatorChat/StandardsMart/FleetMesh use isDomainPeelMiss."""
    root = _ROOT / "packages" / "admin_ui" / "src"
    paths = (
        root / "pages" / "OperatorChatPage.tsx",
        root / "pages" / "StandardsMartPage.tsx",
        root / "pages" / "fleet" / "FleetMeshPanel.tsx",
    )
    for path in paths:
        src = path.read_text(encoding="utf-8")
        assert "sak500-c" in src, path.name
        assert "isDomainPeelMiss" in src, path.name
        assert "isComputeMiss" not in src, path.name
        assert "isReadPeelMiss" not in src, path.name


# --- sak500-d: admin Metrics + CustomAgents domain peel miss ---


def test_sak500_d_admin_metrics_custom_agents_domain_peel_miss() -> None:
    """sak500-d: MetricsPage + CustomAgentsPage use isDomainPeelMiss."""
    pages = _ROOT / "packages" / "admin_ui" / "src" / "pages"
    for name in ("MetricsPage.tsx", "CustomAgentsPage.tsx"):
        src = (pages / name).read_text(encoding="utf-8")
        assert "sak500-d" in src, name
        assert "isDomainPeelMiss" in src, name
        assert "isComputeMiss" not in src, name
        assert "isReadPeelMiss" not in src, name


# --- sak500-e: OpenAPI 503 — custom-agents + standards registry ---


SAK500_E_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/custom-agents", "get"),
    ("/v1/standards/registry", "get"),
)


@pytest.mark.sak500_e
def test_sak500_e_openapi_artifact_documents_peel_503() -> None:
    """sak500-e: openapi.json lists 503 problem+json on custom-agents + standards registry."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK500_E_PEEL_OPENAPI:
        content = (
            spec.get("paths", {})
            .get(path, {})
            .get(method, {})
            .get("responses", {})
            .get("503", {})
            .get("content", {})
            or {}
        )
        assert "application/problem+json" in content, (
            f"missing 503 problem+json on {method.upper()} {path}"
        )


@pytest.mark.sak500_e
def test_sak500_e_routes_wire_openapi_helpers() -> None:
    """sak500-e: custom_agents + standards registry wire long_tail OpenAPI helpers."""
    agents = (_ROOT / "packages" / "api" / "routes" / "custom_agents.py").read_text(
        encoding="utf-8",
    )
    standards = (_ROOT / "packages" / "api" / "routes" / "standards.py").read_text(
        encoding="utf-8",
    )
    assert "sak500-e" in agents
    assert "long_tail_json_openapi_responses()" in agents
    assert "sak500-e" in standards
    assert "long_tail_json_openapi_responses()" in standards


# --- sak500-f: soak/CI close-out (partial epic start) ---


def test_sak500_f_ci_workflow_lists_peel_unit() -> None:
    """sak500-f: nimbusware-peel.yml includes test_sak500_peel.py in peel-unit."""
    workflow = (_ROOT.parent / ".github" / "workflows" / "nimbusware-peel.yml").read_text(
        encoding="utf-8"
    )
    peel_unit = workflow.split("  peel-unit:", 1)[1].split("  peel-flag-matrix:", 1)[0]
    assert "tests/unit/test_sak500_peel.py" in peel_unit


def test_sak500_f_soak_lib_asserts_present() -> None:
    """sak500-f: peel_soak_lib wires Maker ribbon close-out asserts."""
    soak = (_ROOT / "scripts" / "peel_soak_lib.py").read_text(encoding="utf-8")
    assert "_assert_sak500_maker_ribbons" in soak
    assert "sak500 maker ribbons domain peel miss" in soak
    assert 'label.startswith("sak500")' in soak
    assert "sak500-f — Maker ribbons" in soak


# --- sak500-g: Maker sse-client drop isBrokerMiss catch-all ---


def test_sak500_g_sse_client_domain_capacity_only() -> None:
    """sak500-g: parseSsePeelMiss uses domain+capacity only (no isBrokerMiss)."""
    src = (_ROOT / "packages" / "maker_web" / "static" / "js" / "sse-client.js").read_text(
        encoding="utf-8"
    )
    assert "sak500-g" in src
    assert "isBrokerMiss" not in src
    assert "isDomainPeelMiss" in src
    assert "isCapacityMiss" in src


# --- sak500-h: Maker api-client bootstrap domain peel ---


def test_sak500_h_api_client_bootstrap_domain_peel() -> None:
    """sak500-h: isBootstrapPeelMiss uses isDomainPeelMiss."""
    src = (_ROOT / "packages" / "maker_web" / "static" / "js" / "api-client.js").read_text(
        encoding="utf-8"
    )
    assert "sak500-h" in src
    assert "isDomainPeelMiss" in src
    assert "isBrokerMiss" not in src


# --- sak500-i: OpenAPI 503 — projects + preflight-history ---


SAK500_I_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/projects", "get"),
    ("/v1/preflight-history", "get"),
)


@pytest.mark.sak500_i
def test_sak500_i_openapi_artifact_documents_peel_503() -> None:
    """sak500-i: openapi.json lists 503 on projects + preflight-history."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK500_I_PEEL_OPENAPI:
        content = (
            spec.get("paths", {})
            .get(path, {})
            .get(method, {})
            .get("responses", {})
            .get("503", {})
            .get("content", {})
            or {}
        )
        assert "application/problem+json" in content, path


@pytest.mark.sak500_i
def test_sak500_i_routes_wire_openapi_helpers() -> None:
    """sak500-i: projects + preflight wire long_tail OpenAPI helpers."""
    projects = (_ROOT / "packages" / "api" / "routes" / "projects.py").read_text(
        encoding="utf-8",
    )
    preflight = (_ROOT / "packages" / "api" / "routes" / "preflight.py").read_text(
        encoding="utf-8",
    )
    assert "sak500-i" in projects
    assert "long_tail_json_openapi_responses()" in projects
    assert "sak500-i" in preflight
    assert "long_tail_json_openapi_responses()" in preflight


# --- sak500-j: deepen close-out (g–i soak + CI openapi subset) ---


def test_sak500_j_soak_and_ci_deepen() -> None:
    """sak500-j: soak asserts sse/bootstrap; CI lists sak500-i openapi subset."""
    soak = (_ROOT / "scripts" / "peel_soak_lib.py").read_text(encoding="utf-8")
    assert "_assert_sak500_sse_bootstrap" in soak
    assert "sak500-j — Maker residual" in soak
    workflow = (_ROOT.parent / ".github" / "workflows" / "nimbusware-peel.yml").read_text(
        encoding="utf-8"
    )
    assert "sak500_i" in workflow
    assert "sak500_e" in workflow
    assert "test_sak500_peel.py" in workflow

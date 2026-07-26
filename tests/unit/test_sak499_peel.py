from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]


# --- sak499-a: Maker chat tab domain peel miss ---


def test_sak499_a_maker_chat_domain_peel_miss_markers() -> None:
    """sak499-a: chat tabs + session-hub use isDomainPeelMiss (not isBrokerMiss)."""
    js = _ROOT / "packages" / "maker_web" / "static" / "js"
    tabs = js / "tabs"
    with_format = (
        tabs / "chat.js",
        tabs / "chat_agents_ui.js",
        tabs / "chat_discovery_ui.js",
        tabs / "chat_host_transfer_ui.js",
        tabs / "chat_library_ui.js",
        tabs / "chat_optimizer_ui.js",
        tabs / "chat_run_card_ui.js",
        tabs / "chat_session_lifecycle.js",
        tabs / "chat_session_ui.js",
    )
    domain_only = (
        js / "session-hub.js",
        tabs / "chat_escalation_ui.js",
        tabs / "chat_theater_ui.js",
    )
    for path in (*with_format, *domain_only):
        src = path.read_text(encoding="utf-8")
        assert "sak499-a" in src, path.name
        assert "isBrokerMiss" not in src, path.name
        assert "missBannerText" not in src, path.name
        assert "isDomainPeelMiss" in src, path.name
    for path in with_format:
        src = path.read_text(encoding="utf-8")
        assert "formatDomainMissMessage" in src, path.name


# --- sak499-b: Maker models/progress/review/settings/misc tab domain peel miss ---


def test_sak499_b_maker_tab_domain_peel_miss_markers() -> None:
    """sak499-b: batch-2 Maker tabs use isDomainPeelMiss + formatDomainMissMessage."""
    js = _ROOT / "packages" / "maker_web" / "static" / "js"
    tabs = js / "tabs"
    progress = tabs / "progress"
    with_format = (
        tabs / "plan.js",
        tabs / "accessible_compute_ui.js",
        tabs / "models_local_ui.js",
        tabs / "models_ollama_ui.js",
        tabs / "review_git_ui.js",
        tabs / "review_advanced_ui.js",
        tabs / "settings_memory_stitch_ui.js",
        tabs / "settings_agent_routing_ui.js",
        progress / "progress_ribbon_refresh.js",
        progress / "context-panels.js",
        js / "critic-reliability-panel.js",
        js / "standards-ribbon.js",
    )
    domain_only = (
        js / "tab-loader.js",
        progress / "render-chips.js",
        progress / "integrator-ribbon.js",
        tabs / "models_connections_ui.js",
        tabs / "models_subscriptions_ui.js",
        tabs / "settings_governor_ui.js",
    )
    toast_only = (tabs / "settings_optimizer_ui.js",)
    for path in (*with_format, *domain_only, *toast_only):
        src = path.read_text(encoding="utf-8")
        assert "sak499-b" in src, path.name
        assert "isBrokerMiss" not in src, path.name
        assert "missBannerText" not in src, path.name
    for path in with_format:
        src = path.read_text(encoding="utf-8")
        assert "isDomainPeelMiss" in src, path.name
        assert "formatDomainMissMessage" in src, path.name
    for path in domain_only:
        src = path.read_text(encoding="utf-8")
        assert "isDomainPeelMiss" in src, path.name


# --- sak499-c: OpenAPI 503 — bridge-memory + launch-eval ---


import json
import re

import pytest

from api.schemas.openapi import PROBLEM_RESPONSE_503
from api.schemas.peel_responses import (
    ContextArtifactBridgeMissResponse,
    LaunchEvalMissResponse,
    llm_json_openapi_responses,
    memory_json_openapi_responses,
)

SAK499_C_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/projects/{project_id}/context-artifacts/{artifact_id}/bridge-memory", "post"),
    ("/v1/runs/{run_id}/maker/launch-eval", "post"),
)


def _sak499_c_openapi_json_path() -> Path:
    return _ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json"


@pytest.mark.sak499_c
def test_sak499_c_openapi_artifact_documents_peel_503() -> None:
    """sak499-c: openapi.json lists 503 problem+json on bridge-memory + launch-eval."""
    spec = json.loads(_sak499_c_openapi_json_path().read_text(encoding="utf-8"))
    for path, method in SAK499_C_PEEL_OPENAPI:
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
        schema = content["application/problem+json"].get("schema", {})
        assert schema.get("type") == "object"
        assert "code" in schema.get("properties", {})


@pytest.mark.sak499_c
def test_sak499_c_peel_routes_source_wire_openapi_helpers() -> None:
    """sak499-c: project bridge-memory + maker launch-eval wire peel OpenAPI helpers."""
    root = _ROOT / "packages" / "api"
    peel = (root / "schemas" / "peel_responses.py").read_text(encoding="utf-8")
    project_ctx = (root / "routes" / "project_context_artifacts.py").read_text(encoding="utf-8")
    maker = (root / "routes" / "runs" / "maker_approval.py").read_text(encoding="utf-8")

    assert "sak499-c" in peel
    assert memory_json_openapi_responses()[503] is PROBLEM_RESPONSE_503
    assert llm_json_openapi_responses()[503] is PROBLEM_RESPONSE_503
    assert ContextArtifactBridgeMissResponse().via is None
    assert LaunchEvalMissResponse().via is None

    assert "memory_json_openapi_responses(not_found=PROBLEM_RESPONSE_404)" in project_ctx
    assert "sak499-c" in project_ctx

    assert "llm_json_openapi_responses(not_found=PROBLEM_RESPONSE_404)" in maker
    assert "/maker/launch-eval" in maker
    assert "sak499-c" in maker


# --- sak499-d: admin_ui batch domain peel miss migration ---


def test_sak499_d_admin_ui_domain_peel_miss_markers() -> None:
    """sak499-d: admin fleet/run/config pages use isDomainPeelMiss + formatReadCatchMessage."""
    root = _ROOT / "packages" / "admin_ui" / "src"
    pages = (
        root / "pages" / "FleetPage.tsx",
        root / "pages" / "RunDetailPage.tsx",
        root / "pages" / "RunListPage.tsx",
        root / "pages" / "ConfigPage.tsx",
        root / "pages" / "PreflightPage.tsx",
        root / "pages" / "ProjectsPage.tsx",
    )
    components = (
        root / "components" / "TheaterPanel.tsx",
        root / "components" / "TimelineAccordion.tsx",
    )
    hook = root / "hooks" / "useApiGet.ts"
    peel = root / "api" / "peel_assert.ts"
    for path in (*pages, *components, hook):
        src = path.read_text(encoding="utf-8")
        assert "sak499-d" in src, path.name
        assert "isDomainPeelMiss" in src, path.name
        assert "isComputeMiss" not in src, path.name
        assert "isReadPeelMiss" not in src, path.name
        # FleetPage keeps isMemoryMiss for fleet_memory / memory search (sak493-i).
        if path.name != "FleetPage.tsx":
            assert "isMemoryMiss" not in src, path.name
    fleet = (root / "pages" / "FleetPage.tsx").read_text(encoding="utf-8")
    assert "isMemoryMiss" in fleet
    assert "sak499-d" in peel.read_text(encoding="utf-8")


# --- sak499-i: Maker home/build/wizard residual domain peel miss ---


def test_sak499_i_maker_home_build_wizard_domain_peel_miss() -> None:
    """sak499-i: build/wizard/home readiness use domain (or capacity) peel helpers."""
    tabs = _ROOT / "packages" / "maker_web" / "static" / "js" / "tabs"
    build = (tabs / "build.js").read_text(encoding="utf-8")
    wizard = (tabs / "wizard.js").read_text(encoding="utf-8")
    home = (tabs / "home_readiness_ui.js").read_text(encoding="utf-8")
    for src, name in ((build, "build.js"), (wizard, "wizard.js"), (home, "home_readiness_ui.js")):
        assert "sak499-i" in src, name
        assert "isBrokerMiss" not in src, name
    assert "isDomainPeelMiss" in build
    assert "formatDomainMissMessage" in build
    assert "isDomainPeelMiss" in wizard
    assert "formatDomainMissMessage" in wizard
    assert "isDomainPeelMiss" in home
    assert "formatDomainMissMessage" in home
    assert "isCapacityMiss" in home


# --- sak499-e: shared LLM peel_guard ---


def test_sak499_e_peel_guard_module_and_callers() -> None:
    """sak499-e: peel_guard centralizes broker_miss/transport soft-fail detection."""
    from orchestrator.llm.peel_guard import _llm_broker_miss_or_transport

    assert _llm_broker_miss_or_transport(RuntimeError("broker_miss: llm down"))
    assert _llm_broker_miss_or_transport(RuntimeError("Broker miss under LLM=1"))
    assert _llm_broker_miss_or_transport(RuntimeError("transport error"))
    assert not _llm_broker_miss_or_transport(RuntimeError("validation failed"))

    guard = (_ROOT / "packages" / "orchestrator" / "llm" / "peel_guard.py").read_text(
        encoding="utf-8",
    )
    assert "sak499-e" in guard
    callers = (
        _ROOT / "packages" / "orchestrator" / "llm" / "gate_helpers.py",
        _ROOT / "packages" / "orchestrator" / "persona" / "critique_llm.py",
        _ROOT / "packages" / "orchestrator" / "launch" / "launch_evaluator.py",
        _ROOT / "packages" / "orchestrator" / "launch" / "launch_test_llm.py",
        _ROOT / "packages" / "orchestrator" / "test_writer_stage.py",
        _ROOT / "packages" / "orchestrator" / "_pipeline" / "lifecycle_plan.py",
    )
    for path in callers:
        src = path.read_text(encoding="utf-8")
        assert "sak499-e" in src, path.name
        assert "from orchestrator.llm.peel_guard import" in src, path.name


# --- sak499-g: CI matrix deepen (MEMORY/LLM flag-matrix + openapi-503 artifact subset) ---


def test_sak499_g_ci_flag_matrix_deepens() -> None:
    """sak499-g: peel-flag-matrix blocks MEMORY/LLM flags + sak499-c openapi artifact subset."""
    yml = (
        Path(__file__).resolve().parents[3] / ".github" / "workflows" / "nimbusware-peel.yml"
    ).read_text(encoding="utf-8")
    assert "peel-flag-matrix" in yml
    assert "test_memory_broker_flags_api.py" in yml
    assert "test_llm_broker_flags_api.py" in yml
    assert "-m sak499_c" in yml
    assert "test_sak499_peel.py" in yml
    peel_unit = yml.split("  peel-unit:", 1)[1].split("  peel-flag-matrix:", 1)[0]
    bare_compute_wire = re.findall(
        r"tests/unit/test_compute_stage_wire\.py(?!::)",
        peel_unit,
    )
    assert len(bare_compute_wire) == 1


# --- sak499-f: dual_run_route domain HTTP miss consolidation ---


@pytest.mark.sak499_f
def test_sak499_f_map_domain_broker_http_miss_markers() -> None:
    """sak499-f: domain broker_route mappers delegate to map_domain_broker_http_miss."""
    from broker_client.dual_run_route import map_domain_broker_http_miss

    dual_src = (_ROOT / "packages" / "broker_client" / "dual_run_route.py").read_text(
        encoding="utf-8",
    )
    peel_src = (_ROOT / "packages" / "broker_client" / "peel_assert.py").read_text(
        encoding="utf-8",
    )
    routes = (
        _ROOT / "packages" / "memory" / "broker_route.py",
        _ROOT / "packages" / "compute" / "broker_route.py",
        _ROOT / "packages" / "agent_tools" / "broker_route.py",
        _ROOT / "packages" / "executor" / "broker_route.py",
        _ROOT / "packages" / "research" / "broker_route.py",
    )
    assert "sak499-f" in dual_src
    assert "map_domain_broker_http_miss" in dual_src
    assert "normalize_domain_tool_result" in peel_src
    assert "sak499-f" in peel_src
    assert callable(map_domain_broker_http_miss)
    for path in routes:
        src = path.read_text(encoding="utf-8")
        assert "sak499-f" in src, path.name
        assert "map_domain_broker_http_miss" in src, path.name


# --- sak499-j: soak/CI close-out ---


def test_sak499_j_soak_lib_asserts_present() -> None:
    """sak499-j: peel_soak_lib wires peel_guard + Maker domain miss close-out."""
    soak = (_ROOT / "scripts" / "peel_soak_lib.py").read_text(encoding="utf-8")
    assert "_assert_sak499_peel_guard" in soak
    assert "_assert_sak499_maker_domain_miss" in soak
    assert "sak499 peel_guard" in soak
    assert "sak499 maker domain peel miss" in soak
    assert 'label.startswith("sak499")' in soak
    assert "sak499-j — Maker/admin miss parity" in soak


@pytest.mark.sak499_j
def test_sak499_j_ci_workflow_lists_peel_unit() -> None:
    """sak499-j: nimbusware-peel.yml includes test_sak499_peel.py in peel-unit."""
    workflow = (_ROOT.parent / ".github" / "workflows" / "nimbusware-peel.yml").read_text(
        encoding="utf-8"
    )
    assert "test_sak499_peel.py" in workflow
    peel_unit = workflow.split("  peel-unit:", 1)[1].split("  peel-flag-matrix:", 1)[0]
    assert "tests/unit/test_sak499_peel.py" in peel_unit

from __future__ import annotations

import json
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]


# --- sak501-a: HardwarePage domain peel harden ---


def test_sak501_a_hardware_page_domain_peel_miss() -> None:
    """sak501-a: HardwarePage detects domain peel on load + catalog."""
    src = (
        _ROOT / "packages" / "admin_ui" / "src" / "pages" / "HardwarePage.tsx"
    ).read_text(encoding="utf-8")
    assert "sak501-a" in src
    assert "isDomainPeelMiss" in src
    assert "isCapacityMiss" in src
    assert "formatPeelMissMessage" in src


# --- sak501-b: OpenAPI 503 — platform user-profiles ---


SAK501_B_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/platform/autopilot/user-profiles", "get"),
    ("/v1/platform/enforcement/user-profiles", "get"),
)


@pytest.mark.sak501_b
def test_sak501_b_openapi_user_profiles_503() -> None:
    """sak501-b: openapi.json + routes wire 503 on user-profiles GETs."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK501_B_PEEL_OPENAPI:
        content = (
            spec["paths"][path][method]["responses"]["503"]["content"]
        )
        assert "application/problem+json" in content, path
    src = (
        _ROOT / "packages" / "api" / "routes" / "platform_user_profiles.py"
    ).read_text(encoding="utf-8")
    assert src.count("sak501-b") >= 2
    assert "long_tail_json_openapi_responses()" in src


# --- sak501-c: OpenAPI 503 — run autopilot/enforcement/interjection ---


SAK501_C_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/runs/{run_id}/enforcement", "get"),
    ("/v1/runs/{run_id}/interjection-queue", "get"),
    ("/v1/runs/{run_id}/autopilot", "get"),
)


@pytest.mark.sak501_c
def test_sak501_c_openapi_run_ribbons_503() -> None:
    """sak501-c: openapi.json + routes wire 503 on run ribbon GETs."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK501_C_PEEL_OPENAPI:
        content = (
            spec["paths"][path][method]["responses"]["503"]["content"]
        )
        assert "application/problem+json" in content, path
    for rel in (
        "runs/enforcement.py",
        "runs/interjection.py",
        "runs/autopilot.py",
    ):
        src = (_ROOT / "packages" / "api" / "routes" / rel).read_text(encoding="utf-8")
        assert "sak501-c" in src, rel
        assert "long_tail_json_openapi_responses()" in src, rel


# --- sak501-d: Maker formatCapacityMissMessage ---


def test_sak501_d_maker_format_capacity_miss() -> None:
    """sak501-d: broker_miss exports formatCapacityMissMessage; home readiness uses it."""
    miss = (
        _ROOT / "packages" / "maker_web" / "static" / "js" / "broker_miss.js"
    ).read_text(encoding="utf-8")
    home = (
        _ROOT
        / "packages"
        / "maker_web"
        / "static"
        / "js"
        / "tabs"
        / "home_readiness_ui.js"
    ).read_text(encoding="utf-8")
    assert "sak501-d" in miss
    assert "export function formatCapacityMissMessage" in miss
    assert "sak501-d" in home
    assert "formatCapacityMissMessage" in home
    assert "missBannerText" not in home


# --- sak501-e: CI deepen openapi subsets ---


def test_sak501_e_ci_openapi_subsets() -> None:
    """sak501-e: peel-flag-matrix runs sak501 OpenAPI marker subsets."""
    yml = (
        _ROOT.parent / ".github" / "workflows" / "nimbusware-peel.yml"
    ).read_text(encoding="utf-8")
    assert "sak501_b" in yml
    assert "sak501_c" in yml
    assert "test_sak501_peel.py" in yml


# --- sak501-f: soak/CI close-out ---


def test_sak501_f_soak_and_ci_closeout() -> None:
    """sak501-f: peel_soak_lib + peel-unit list test_sak501_peel.py."""
    soak = (_ROOT / "scripts" / "peel_soak_lib.py").read_text(encoding="utf-8")
    assert "_assert_sak501_hardware_capacity_formatter" in soak
    assert "sak501-f — Hardware domain" in soak
    assert 'label.startswith("sak501")' in soak
    workflow = (
        _ROOT.parent / ".github" / "workflows" / "nimbusware-peel.yml"
    ).read_text(encoding="utf-8")
    peel_unit = workflow.split("  peel-unit:", 1)[1].split("  peel-flag-matrix:", 1)[0]
    assert "tests/unit/test_sak501_peel.py" in peel_unit


# --- sak501-g: OpenAPI 503 — settings catalog/install ---


SAK501_G_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/settings/catalog", "get"),
    ("/v1/settings/install", "get"),
)


@pytest.mark.sak501_g
def test_sak501_g_openapi_settings_503() -> None:
    """sak501-g: settings catalog/install document 503 + route markers."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK501_G_PEEL_OPENAPI:
        assert "application/problem+json" in (
            spec["paths"][path][method]["responses"]["503"]["content"]
        ), path
    src = (_ROOT / "packages" / "api" / "routes" / "operator_settings.py").read_text(
        encoding="utf-8",
    )
    assert src.count("sak501-g") >= 2


# --- sak501-h: OpenAPI 503 — model-bindings ---


SAK501_H_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/platform/model-bindings/preflight", "get"),
    ("/v1/platform/model-bindings/defaults", "get"),
)


@pytest.mark.sak501_h
def test_sak501_h_openapi_model_bindings_503() -> None:
    """sak501-h: model-bindings preflight/defaults document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK501_H_PEEL_OPENAPI:
        assert "application/problem+json" in (
            spec["paths"][path][method]["responses"]["503"]["content"]
        ), path
    src = (_ROOT / "packages" / "api" / "routes" / "model_bindings.py").read_text(
        encoding="utf-8",
    )
    assert src.count("sak501-h") >= 2


# --- sak501-i: OpenAPI 503 — maker push + operator-profiles ---


SAK501_I_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/maker/push-subscriptions", "get"),
    ("/v1/platform/operator-profiles", "get"),
)


@pytest.mark.sak501_i
def test_sak501_i_openapi_push_operator_profiles_503() -> None:
    """sak501-i: push-subscriptions + operator-profiles document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK501_I_PEEL_OPENAPI:
        assert "application/problem+json" in (
            spec["paths"][path][method]["responses"]["503"]["content"]
        ), path
    push = (_ROOT / "packages" / "api" / "routes" / "maker_push.py").read_text(
        encoding="utf-8",
    )
    profiles = (
        _ROOT / "packages" / "api" / "routes" / "platform_operator_profiles.py"
    ).read_text(encoding="utf-8")
    assert "sak501-i" in push
    assert "sak501-i" in profiles


# --- sak501-j: deepen close-out g–i ---


def test_sak501_j_soak_and_ci_deepen() -> None:
    """sak501-j: soak OpenAPI route asserts + CI sak501_g/h/i markers."""
    soak = (_ROOT / "scripts" / "peel_soak_lib.py").read_text(encoding="utf-8")
    assert "_assert_sak501_openapi_settings_bindings" in soak
    assert "sak501-j — settings/bindings/push OpenAPI" in soak
    yml = (
        _ROOT.parent / ".github" / "workflows" / "nimbusware-peel.yml"
    ).read_text(encoding="utf-8")
    assert "sak501_g" in yml
    assert "sak501_h" in yml
    assert "sak501_i" in yml

from __future__ import annotations

import json
from pathlib import Path

import pytest

from api.schemas.peel_responses import count_missing_peel_503, list_missing_peel_503

_ROOT = Path(__file__).resolve().parents[2]


# --- sak509-a: OpenAPI 503 — hardware fleet GET + rescan ---


SAK509_A_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/platform/hardware/fleet", "get"),
    ("/v1/platform/hardware/fleet/rescan", "post"),
)


@pytest.mark.sak509_a
def test_sak509_a_openapi_hardware_fleet_503() -> None:
    """sak509-a: hardware fleet GET + rescan document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK509_A_PEEL_OPENAPI:
        assert "application/problem+json" in (
            spec["paths"][path][method]["responses"]["503"]["content"]
        ), path
    assert "sak509-a" in (
        _ROOT / "packages" / "api" / "routes" / "platform_hardware.py"
    ).read_text(encoding="utf-8")


# --- sak509-b: OpenAPI 503 — models catalog-info + ranked ---


SAK509_B_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/platform/models/catalog-info", "get"),
    ("/v1/platform/models/ranked", "get"),
)


@pytest.mark.sak509_b
def test_sak509_b_openapi_models_catalog_ranked_503() -> None:
    """sak509-b: models catalog-info + ranked document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK509_B_PEEL_OPENAPI:
        assert "application/problem+json" in (
            spec["paths"][path][method]["responses"]["503"]["content"]
        ), path
    assert "sak509-b" in (
        _ROOT / "packages" / "api" / "routes" / "platform_model_routing.py"
    ).read_text(encoding="utf-8")


# --- sak509-c: OpenAPI 503 — apply-preset + routing-presets ---


SAK509_C_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/platform/models/apply-preset", "post"),
    ("/v1/platform/routing-presets", "get"),
)


@pytest.mark.sak509_c
def test_sak509_c_openapi_preset_routing_503() -> None:
    """sak509-c: apply-preset + routing-presets document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK509_C_PEEL_OPENAPI:
        assert "application/problem+json" in (
            spec["paths"][path][method]["responses"]["503"]["content"]
        ), path
    assert "sak509-c" in (
        _ROOT / "packages" / "api" / "routes" / "platform_model_routing.py"
    ).read_text(encoding="utf-8")


# --- sak509-d: count_missing_peel_503 DRY via list_missing ---


@pytest.mark.sak509_d
def test_sak509_d_count_missing_uses_list_missing() -> None:
    """sak509-d: count_missing_peel_503 delegates to list_missing_peel_503."""
    peel = (_ROOT / "packages" / "api" / "schemas" / "peel_responses.py").read_text(
        encoding="utf-8",
    )
    assert "sak509-d" in peel
    assert "return len(list_missing_peel_503" in peel
    paths = {
        "/t": {"get": {"responses": {"200": {"description": "ok"}}}},
        "/u": {"post": {"responses": {"200": {"description": "ok"}, "503": {}}}},
    }
    targets = [("/t", "get"), ("/u", "post")]
    assert count_missing_peel_503(paths, targets) == len(
        list_missing_peel_503(paths, targets),
    )
    assert count_missing_peel_503(paths, targets) == 1


# --- sak509-e: CI OpenAPI subsets ---


def test_sak509_e_ci_openapi_subsets() -> None:
    """sak509-e: peel-flag-matrix runs sak509 OpenAPI marker subsets."""
    yml = (
        _ROOT.parent / ".github" / "workflows" / "nimbusware-peel.yml"
    ).read_text(encoding="utf-8")
    assert "sak509_a" in yml
    assert "sak509_b" in yml
    assert "sak509_c" in yml
    assert "test_sak509_peel.py" in yml


# --- sak509-f: soak/CI close-out ---


def test_sak509_f_soak_and_ci_closeout() -> None:
    """sak509-f: peel_soak_lib + peel-unit list test_sak509_peel.py."""
    soak = (_ROOT / "scripts" / "peel_soak_lib.py").read_text(encoding="utf-8")
    assert "_assert_sak509_count_missing_dry" in soak
    assert "sak509-f — hardware fleet/models OpenAPI + count_missing DRY" in soak
    assert 'label.startswith("sak509")' in soak
    workflow = (
        _ROOT.parent / ".github" / "workflows" / "nimbusware-peel.yml"
    ).read_text(encoding="utf-8")
    peel_unit = workflow.split("  peel-unit:", 1)[1].split("  peel-flag-matrix:", 1)[0]
    assert "tests/unit/test_sak509_peel.py" in peel_unit


# --- sak509-g: OpenAPI 503 — routing-presets apply + model dependencies ---


SAK509_G_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/platform/routing-presets/apply", "post"),
    ("/v1/platform/models/dependencies", "get"),
)


@pytest.mark.sak509_g
def test_sak509_g_openapi_routing_deps_503() -> None:
    """sak509-g: routing-presets apply + models dependencies document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK509_G_PEEL_OPENAPI:
        assert "application/problem+json" in (
            spec["paths"][path][method]["responses"]["503"]["content"]
        ), path
    assert "sak509-g" in (
        _ROOT / "packages" / "api" / "routes" / "platform_model_routing.py"
    ).read_text(encoding="utf-8")


# --- sak509-h: OpenAPI 503 — invite-templates + edition ---


SAK509_H_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/platform/invite-templates", "get"),
    ("/v1/platform/edition", "get"),
)


@pytest.mark.sak509_h
def test_sak509_h_openapi_invite_edition_503() -> None:
    """sak509-h: invite-templates + edition document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK509_H_PEEL_OPENAPI:
        assert "application/problem+json" in (
            spec["paths"][path][method]["responses"]["503"]["content"]
        ), path
    assert "sak509-h" in (
        _ROOT / "packages" / "api" / "routes" / "platform.py"
    ).read_text(encoding="utf-8")


# --- sak509-i: OpenAPI 503 — collab-settings GET/PUT ---


SAK509_I_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/platform/collab-settings", "get"),
    ("/v1/platform/collab-settings", "put"),
)


@pytest.mark.sak509_i
def test_sak509_i_openapi_collab_settings_503() -> None:
    """sak509-i: collab-settings GET/PUT document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK509_I_PEEL_OPENAPI:
        assert "application/problem+json" in (
            spec["paths"][path][method]["responses"]["503"]["content"]
        ), path
    assert "sak509-i" in (
        _ROOT / "packages" / "api" / "routes" / "platform.py"
    ).read_text(encoding="utf-8")


# --- sak509-j: soak/CI deepen ---


def test_sak509_j_soak_and_ci_deepen() -> None:
    """sak509-j: soak platform residual OpenAPI asserts + CI sak509_g/h/i markers."""
    soak = (_ROOT / "scripts" / "peel_soak_lib.py").read_text(encoding="utf-8")
    assert "_assert_sak509_platform_residual_openapi" in soak
    assert "sak509-j — routing/invite/collab OpenAPI" in soak
    yml = (
        _ROOT.parent / ".github" / "workflows" / "nimbusware-peel.yml"
    ).read_text(encoding="utf-8")
    assert "sak509_g" in yml
    assert "sak509_h" in yml
    assert "sak509_i" in yml

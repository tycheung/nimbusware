from __future__ import annotations

import json
from pathlib import Path

import pytest

from api.schemas.peel_responses import patch_openapi_json_peel_503

_ROOT = Path(__file__).resolve().parents[2]


# --- sak510-a: OpenAPI 503 — readiness + fleet-governance ---


SAK510_A_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/platform/readiness", "get"),
    ("/v1/platform/fleet-governance", "get"),
)


@pytest.mark.sak510_a
def test_sak510_a_openapi_readiness_governance_503() -> None:
    """sak510-a: readiness + fleet-governance document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK510_A_PEEL_OPENAPI:
        assert "application/problem+json" in (
            spec["paths"][path][method]["responses"]["503"]["content"]
        ), path
    assert "sak510-a" in (
        _ROOT / "packages" / "api" / "routes" / "platform.py"
    ).read_text(encoding="utf-8")


# --- sak510-b: OpenAPI 503 — onboarding GET/POST ---


SAK510_B_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/platform/onboarding", "get"),
    ("/v1/platform/onboarding", "post"),
)


@pytest.mark.sak510_b
def test_sak510_b_openapi_onboarding_503() -> None:
    """sak510-b: onboarding GET/POST document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK510_B_PEEL_OPENAPI:
        assert "application/problem+json" in (
            spec["paths"][path][method]["responses"]["503"]["content"]
        ), path
    assert "sak510-b" in (
        _ROOT / "packages" / "api" / "routes" / "platform.py"
    ).read_text(encoding="utf-8")


# --- sak510-c: OpenAPI 503 — optimizer-weights GET/PUT ---


SAK510_C_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/platform/optimizer-weights", "get"),
    ("/v1/platform/optimizer-weights", "put"),
)


@pytest.mark.sak510_c
def test_sak510_c_openapi_optimizer_weights_503() -> None:
    """sak510-c: optimizer-weights GET/PUT document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK510_C_PEEL_OPENAPI:
        assert "application/problem+json" in (
            spec["paths"][path][method]["responses"]["503"]["content"]
        ), path
    assert "sak510-c" in (
        _ROOT / "packages" / "api" / "routes" / "platform.py"
    ).read_text(encoding="utf-8")


# --- sak510-d: patch_openapi_json_peel_503 helper ---


@pytest.mark.sak510_d
def test_sak510_d_patch_openapi_json_peel_503(tmp_path: Path) -> None:
    """sak510-d: patch_openapi_json_peel_503 writes 503 into a file once."""
    peel = (_ROOT / "packages" / "api" / "schemas" / "peel_responses.py").read_text(
        encoding="utf-8",
    )
    assert "sak510-d" in peel
    assert "def patch_openapi_json_peel_503" in peel
    path = tmp_path / "openapi.json"
    path.write_text(
        json.dumps(
            {
                "paths": {
                    "/t": {"get": {"responses": {"200": {"description": "ok"}}}},
                },
            },
        ),
        encoding="utf-8",
    )
    assert patch_openapi_json_peel_503(path, [("/t", "get")]) == 1
    spec = json.loads(path.read_text(encoding="utf-8"))
    assert "503" in spec["paths"]["/t"]["get"]["responses"]
    assert patch_openapi_json_peel_503(path, [("/t", "get")]) == 0


# --- sak510-e: CI OpenAPI subsets ---


def test_sak510_e_ci_openapi_subsets() -> None:
    """sak510-e: peel-flag-matrix runs sak510 OpenAPI marker subsets."""
    yml = (
        _ROOT.parent / ".github" / "workflows" / "nimbusware-peel.yml"
    ).read_text(encoding="utf-8")
    assert "sak510_a" in yml
    assert "sak510_b" in yml
    assert "sak510_c" in yml
    assert "test_sak510_peel.py" in yml


# --- sak510-f: soak/CI close-out ---


def test_sak510_f_soak_and_ci_closeout() -> None:
    """sak510-f: peel_soak_lib + peel-unit list test_sak510_peel.py."""
    soak = (_ROOT / "scripts" / "peel_soak_lib.py").read_text(encoding="utf-8")
    assert "_assert_sak510_patch_openapi_helper" in soak
    assert "sak510-f — readiness/onboarding/optimizer OpenAPI + patch helper" in soak
    assert 'label.startswith("sak510")' in soak
    workflow = (
        _ROOT.parent / ".github" / "workflows" / "nimbusware-peel.yml"
    ).read_text(encoding="utf-8")
    peel_unit = workflow.split("  peel-unit:", 1)[1].split("  peel-flag-matrix:", 1)[0]
    assert "tests/unit/test_sak510_peel.py" in peel_unit


# --- sak510-g: OpenAPI 503 — workspace-precommit + industry-critic-packs ---


SAK510_G_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/platform/workspace-precommit", "post"),
    ("/v1/platform/industry-critic-packs", "get"),
)


@pytest.mark.sak510_g
def test_sak510_g_openapi_precommit_critic_packs_503() -> None:
    """sak510-g: workspace-precommit + industry-critic-packs document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK510_G_PEEL_OPENAPI:
        assert "application/problem+json" in (
            spec["paths"][path][method]["responses"]["503"]["content"]
        ), path
    assert "sak510-g" in (
        _ROOT / "packages" / "api" / "routes" / "platform.py"
    ).read_text(encoding="utf-8")


# --- sak510-h: OpenAPI 503 — safe-coding-preferences ---


SAK510_H_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/platform/safe-coding-preferences", "get"),
    ("/v1/platform/safe-coding-preferences", "put"),
)


@pytest.mark.sak510_h
def test_sak510_h_openapi_safe_coding_503() -> None:
    """sak510-h: safe-coding-preferences GET/PUT document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK510_H_PEEL_OPENAPI:
        assert "application/problem+json" in (
            spec["paths"][path][method]["responses"]["503"]["content"]
        ), path
    assert "sak510-h" in (
        _ROOT / "packages" / "api" / "routes" / "platform.py"
    ).read_text(encoding="utf-8")


# --- sak510-i: OpenAPI 503 — model-bindings defaults PUT + roles ---


SAK510_I_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/platform/model-bindings/defaults", "put"),
    ("/v1/platform/model-bindings/roles", "get"),
)


@pytest.mark.sak510_i
def test_sak510_i_openapi_model_bindings_503() -> None:
    """sak510-i: model-bindings defaults PUT + roles document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK510_I_PEEL_OPENAPI:
        assert "application/problem+json" in (
            spec["paths"][path][method]["responses"]["503"]["content"]
        ), path
    assert "sak510-i" in (
        _ROOT / "packages" / "api" / "routes" / "model_bindings.py"
    ).read_text(encoding="utf-8")


# --- sak510-j: soak/CI deepen ---


def test_sak510_j_soak_and_ci_deepen() -> None:
    """sak510-j: soak prefs/bindings OpenAPI asserts + CI sak510_g/h/i markers."""
    soak = (_ROOT / "scripts" / "peel_soak_lib.py").read_text(encoding="utf-8")
    assert "_assert_sak510_prefs_bindings_openapi" in soak
    assert "sak510-j — precommit/safe-coding/bindings OpenAPI" in soak
    yml = (
        _ROOT.parent / ".github" / "workflows" / "nimbusware-peel.yml"
    ).read_text(encoding="utf-8")
    assert "sak510_g" in yml
    assert "sak510_h" in yml
    assert "sak510_i" in yml

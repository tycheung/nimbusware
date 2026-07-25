from __future__ import annotations

import json
from pathlib import Path

import pytest

from api.schemas.peel_responses import ensure_paths_peel_503

_ROOT = Path(__file__).resolve().parents[2]


# --- sak518-a: OpenAPI 503 — terminate-restart + settings/system GET ---


SAK518_A_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/compute/work-units/{work_unit_id}/terminate-restart", "post"),
    ("/v1/settings/system", "get"),
)


@pytest.mark.sak518_a
def test_sak518_a_openapi_terminate_settings_system_get_503() -> None:
    """sak518-a: terminate-restart + settings/system GET document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK518_A_PEEL_OPENAPI:
        assert "application/problem+json" in (
            spec["paths"][path][method]["responses"]["503"]["content"]
        ), path
    assert "sak518-a" in (
        _ROOT / "packages" / "api" / "routes" / "compute.py"
    ).read_text(encoding="utf-8")
    assert "sak518-a" in (
        _ROOT / "packages" / "api" / "routes" / "operator_settings.py"
    ).read_text(encoding="utf-8")


# --- sak518-b: OpenAPI 503 — settings/system PATCH + settings/me GET ---


SAK518_B_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/settings/system", "patch"),
    ("/v1/settings/me", "get"),
)


@pytest.mark.sak518_b
def test_sak518_b_openapi_settings_system_patch_me_get_503() -> None:
    """sak518-b: settings/system PATCH + settings/me GET document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK518_B_PEEL_OPENAPI:
        assert "application/problem+json" in (
            spec["paths"][path][method]["responses"]["503"]["content"]
        ), path
    assert "sak518-b" in (
        _ROOT / "packages" / "api" / "routes" / "operator_settings.py"
    ).read_text(encoding="utf-8")


# --- sak518-c: OpenAPI 503 — settings/me PATCH + fleet-mesh ---


SAK518_C_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/settings/me", "patch"),
    ("/v1/enterprise/fleet-mesh/status", "get"),
)


@pytest.mark.sak518_c
def test_sak518_c_openapi_settings_me_patch_fleet_mesh_503() -> None:
    """sak518-c: settings/me PATCH + fleet-mesh status document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK518_C_PEEL_OPENAPI:
        assert "application/problem+json" in (
            spec["paths"][path][method]["responses"]["503"]["content"]
        ), path
    assert "sak518-c" in (
        _ROOT / "packages" / "api" / "routes" / "operator_settings.py"
    ).read_text(encoding="utf-8")
    assert "sak518-c" in (
        _ROOT / "packages" / "api" / "routes" / "enterprise" / "fleet_mesh.py"
    ).read_text(encoding="utf-8")


# --- sak518-d: ensure_paths_peel_503 skips absent ops ---


@pytest.mark.sak518_d
def test_sak518_d_ensure_paths_skips_absent() -> None:
    """sak518-d: ensure_paths_peel_503 skips missing path/method pairs."""
    peel = (_ROOT / "packages" / "api" / "schemas" / "peel_responses.py").read_text(
        encoding="utf-8",
    )
    assert "sak518-d" in peel
    assert "Skips targets whose path/method is absent" in peel
    paths = {
        "/t": {"get": {"responses": {"200": {"description": "ok"}}}},
    }
    added = ensure_paths_peel_503(
        paths,
        [("/t", "get"), ("/gone", "post"), ("/t", "delete")],
    )
    assert added == 1
    assert "503" in paths["/t"]["get"]["responses"]
    assert "/gone" not in paths


# --- sak518-e: CI OpenAPI subsets ---


def test_sak518_e_ci_openapi_subsets() -> None:
    """sak518-e: peel-flag-matrix runs sak518 OpenAPI marker subsets."""
    yml = (
        _ROOT.parent / ".github" / "workflows" / "nimbusware-peel.yml"
    ).read_text(encoding="utf-8")
    assert "sak518_a" in yml
    assert "sak518_b" in yml
    assert "sak518_c" in yml
    assert "test_sak518_peel.py" in yml


# --- sak518-f: soak/CI close-out ---


def test_sak518_f_soak_and_ci_closeout() -> None:
    """sak518-f: peel_soak_lib + peel-unit list test_sak518_peel.py."""
    soak = (_ROOT / "scripts" / "peel_soak_lib.py").read_text(encoding="utf-8")
    assert "_assert_sak518_ensure_paths_skip_helper" in soak
    assert "sak518-f — settings/fleet-mesh OpenAPI + ensure_paths skip" in soak
    assert 'label.startswith("sak518")' in soak
    workflow = (
        _ROOT.parent / ".github" / "workflows" / "nimbusware-peel.yml"
    ).read_text(encoding="utf-8")
    peel_unit = workflow.split("  peel-unit:", 1)[1].split("  peel-flag-matrix:", 1)[0]
    assert "tests/unit/test_sak518_peel.py" in peel_unit


# --- sak518-g: OpenAPI 503 — fleet-ollama-sli ---


SAK518_G_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/enterprise/fleet-ollama-sli/status", "get"),
    ("/v1/enterprise/fleet-ollama-sli/preflight-aggregate", "get"),
)


@pytest.mark.sak518_g
def test_sak518_g_openapi_fleet_ollama_sli_503() -> None:
    """sak518-g: fleet-ollama-sli status + preflight-aggregate document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK518_G_PEEL_OPENAPI:
        assert "application/problem+json" in (
            spec["paths"][path][method]["responses"]["503"]["content"]
        ), path
    assert "sak518-g" in (
        _ROOT / "packages" / "api" / "routes" / "enterprise" / "fleet_ops.py"
    ).read_text(encoding="utf-8")


# --- sak518-h: OpenAPI 503 — enforcement + standards policy PUT ---


SAK518_H_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/enterprise/tenants/{tenant_ref}/enforcement-policy", "put"),
    ("/v1/enterprise/tenants/{tenant_ref}/standards-policy", "put"),
)


@pytest.mark.sak518_h
def test_sak518_h_openapi_enforcement_standards_put_503() -> None:
    """sak518-h: enforcement/standards policy PUTs document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK518_H_PEEL_OPENAPI:
        assert "application/problem+json" in (
            spec["paths"][path][method]["responses"]["503"]["content"]
        ), path
    assert "sak518-h" in (
        _ROOT / "packages" / "api" / "routes" / "enterprise" / "fleet_enforcement.py"
    ).read_text(encoding="utf-8")
    assert "sak518-h" in (
        _ROOT / "packages" / "api" / "routes" / "enterprise" / "fleet_standards.py"
    ).read_text(encoding="utf-8")


# --- sak518-i: OpenAPI 503 — slice-policy GET + PUT ---


SAK518_I_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/enterprise/tenants/{tenant_ref}/slice-policy", "get"),
    ("/v1/enterprise/tenants/{tenant_ref}/slice-policy", "put"),
)


@pytest.mark.sak518_i
def test_sak518_i_openapi_slice_policy_503() -> None:
    """sak518-i: slice-policy GET/PUT document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK518_I_PEEL_OPENAPI:
        assert "application/problem+json" in (
            spec["paths"][path][method]["responses"]["503"]["content"]
        ), path
    assert "sak518-i" in (
        _ROOT / "packages" / "api" / "routes" / "enterprise" / "fleet_tenant_policies.py"
    ).read_text(encoding="utf-8")


# --- sak518-j: soak/CI deepen ---


def test_sak518_j_soak_and_ci_deepen() -> None:
    """sak518-j: soak/CI cover fleet-ollama/tenant-policy OpenAPI deepen."""
    soak = (_ROOT / "scripts" / "peel_soak_lib.py").read_text(encoding="utf-8")
    assert "_assert_sak518_fleet_policy_openapi" in soak
    assert "sak518-j — fleet-ollama/tenant-policy OpenAPI" in soak
    yml = (
        _ROOT.parent / ".github" / "workflows" / "nimbusware-peel.yml"
    ).read_text(encoding="utf-8")
    assert "sak518_g" in yml
    assert "sak518_h" in yml
    assert "sak518_i" in yml

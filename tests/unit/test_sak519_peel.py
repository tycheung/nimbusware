from __future__ import annotations

import json
from pathlib import Path

import pytest

from api.schemas.peel_responses import openapi_peel_503_complete_in_file

_ROOT = Path(__file__).resolve().parents[2]


# --- sak519-a: OpenAPI 503 — stack-policy GET + PUT ---


SAK519_A_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/enterprise/tenants/{tenant_ref}/stack-policy", "get"),
    ("/v1/enterprise/tenants/{tenant_ref}/stack-policy", "put"),
)


@pytest.mark.sak519_a
def test_sak519_a_openapi_stack_policy_503() -> None:
    """sak519-a: stack-policy GET/PUT document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK519_A_PEEL_OPENAPI:
        assert (
            "application/problem+json"
            in (spec["paths"][path][method]["responses"]["503"]["content"])
        ), path
    assert "sak519-a" in (
        _ROOT / "packages" / "api" / "routes" / "enterprise" / "fleet_tenant_policies.py"
    ).read_text(encoding="utf-8")


# --- sak519-b: OpenAPI 503 — deploy + discovery policy PUT ---


SAK519_B_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/enterprise/tenants/{tenant_ref}/deploy-policy", "put"),
    ("/v1/enterprise/tenants/{tenant_ref}/discovery-policy", "put"),
)


@pytest.mark.sak519_b
def test_sak519_b_openapi_deploy_discovery_put_503() -> None:
    """sak519-b: deploy/discovery policy PUTs document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK519_B_PEEL_OPENAPI:
        assert (
            "application/problem+json"
            in (spec["paths"][path][method]["responses"]["503"]["content"])
        ), path
    assert "sak519-b" in (
        _ROOT / "packages" / "api" / "routes" / "enterprise" / "fleet_deploy.py"
    ).read_text(encoding="utf-8")
    assert "sak519-b" in (
        _ROOT / "packages" / "api" / "routes" / "enterprise" / "fleet_discovery.py"
    ).read_text(encoding="utf-8")


# --- sak519-c: OpenAPI 503 — audit-policy GET + PUT ---


SAK519_C_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/enterprise/audit-policy", "get"),
    ("/v1/enterprise/audit-policy", "put"),
)


@pytest.mark.sak519_c
def test_sak519_c_openapi_audit_policy_503() -> None:
    """sak519-c: audit-policy GET/PUT document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK519_C_PEEL_OPENAPI:
        assert (
            "application/problem+json"
            in (spec["paths"][path][method]["responses"]["503"]["content"])
        ), path
    assert "sak519-c" in (
        _ROOT / "packages" / "api" / "routes" / "enterprise" / "audit_policy.py"
    ).read_text(encoding="utf-8")


# --- sak519-d: openapi_peel_503_complete_in_file DRY ---


@pytest.mark.sak519_d
def test_sak519_d_complete_in_file_uses_count(tmp_path: Path) -> None:
    """sak519-d: openapi_peel_503_complete_in_file DRYs via count_missing."""
    peel = (_ROOT / "packages" / "api" / "schemas" / "peel_responses.py").read_text(
        encoding="utf-8",
    )
    assert "sak519-d" in peel
    assert "count_missing_peel_503_in_openapi_json" in peel
    path = tmp_path / "openapi.json"
    path.write_text(
        json.dumps(
            {
                "paths": {
                    "/t": {"get": {"responses": {"200": {"description": "ok"}, "503": {}}}},
                    "/u": {"post": {"responses": {"200": {"description": "ok"}}}},
                },
            },
        ),
        encoding="utf-8",
    )
    assert openapi_peel_503_complete_in_file(path, [("/t", "get")]) is True
    assert openapi_peel_503_complete_in_file(path, [("/t", "get"), ("/u", "post")]) is False


# --- sak519-e: CI OpenAPI subsets ---


def test_sak519_e_ci_openapi_subsets() -> None:
    """sak519-e: peel-flag-matrix runs sak519 OpenAPI marker subsets."""
    yml = (_ROOT.parent / ".github" / "workflows" / "nimbusware-peel.yml").read_text(
        encoding="utf-8"
    )
    assert "sak519_a" in yml
    assert "sak519_b" in yml
    assert "sak519_c" in yml
    assert "test_sak519_peel.py" in yml


# --- sak519-f: soak/CI close-out ---


def test_sak519_f_soak_and_ci_closeout() -> None:
    """sak519-f: peel_soak_lib + peel-unit list test_sak519_peel.py."""
    soak = (_ROOT / "scripts" / "peel_soak_lib.py").read_text(encoding="utf-8")
    assert "_assert_sak519_complete_in_file_dry_helper" in soak
    assert "sak519-f — stack/deploy/audit OpenAPI + complete-in-file DRY" in soak
    assert 'label.startswith("sak519")' in soak
    workflow = (_ROOT.parent / ".github" / "workflows" / "nimbusware-peel.yml").read_text(
        encoding="utf-8"
    )
    peel_unit = workflow.split("  peel-unit:", 1)[1].split("  peel-flag-matrix:", 1)[0]
    assert "tests/unit/test_sak519_peel.py" in peel_unit


# --- sak519-g: OpenAPI 503 — model-policy GET + PUT ---


SAK519_G_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/model-policy", "get"),
    ("/v1/model-policy", "put"),
)


@pytest.mark.sak519_g
def test_sak519_g_openapi_model_policy_503() -> None:
    """sak519-g: model-policy GET/PUT document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK519_G_PEEL_OPENAPI:
        assert (
            "application/problem+json"
            in (spec["paths"][path][method]["responses"]["503"]["content"])
        ), path
    assert "sak519-g" in (
        _ROOT / "packages" / "api" / "routes" / "enterprise" / "model_policy.py"
    ).read_text(encoding="utf-8")


# --- sak519-h: OpenAPI 503 — collab-policy GET + PUT ---


SAK519_H_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/collab-policy", "get"),
    ("/v1/collab-policy", "put"),
)


@pytest.mark.sak519_h
def test_sak519_h_openapi_collab_policy_503() -> None:
    """sak519-h: collab-policy GET/PUT document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK519_H_PEEL_OPENAPI:
        assert (
            "application/problem+json"
            in (spec["paths"][path][method]["responses"]["503"]["content"])
        ), path
    assert "sak519-h" in (
        _ROOT / "packages" / "api" / "routes" / "enterprise" / "collab_policy.py"
    ).read_text(encoding="utf-8")


# --- sak519-i: OpenAPI 503 — tenant collab-policy GET + PUT ---


SAK519_I_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/enterprise/tenants/{tenant_ref}/collab-policy", "get"),
    ("/v1/enterprise/tenants/{tenant_ref}/collab-policy", "put"),
)


@pytest.mark.sak519_i
def test_sak519_i_openapi_tenant_collab_policy_503() -> None:
    """sak519-i: tenant collab-policy GET/PUT document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK519_I_PEEL_OPENAPI:
        assert (
            "application/problem+json"
            in (spec["paths"][path][method]["responses"]["503"]["content"])
        ), path
    assert "sak519-i" in (
        _ROOT / "packages" / "api" / "routes" / "enterprise" / "tenant_collab_policy.py"
    ).read_text(encoding="utf-8")


# --- sak519-j: soak/CI deepen ---


def test_sak519_j_soak_and_ci_deepen() -> None:
    """sak519-j: soak/CI cover model/collab-policy OpenAPI deepen."""
    soak = (_ROOT / "scripts" / "peel_soak_lib.py").read_text(encoding="utf-8")
    assert "_assert_sak519_policy_openapi" in soak
    assert "sak519-j — model/collab-policy OpenAPI" in soak
    yml = (_ROOT.parent / ".github" / "workflows" / "nimbusware-peel.yml").read_text(
        encoding="utf-8"
    )
    assert "sak519_g" in yml
    assert "sak519_h" in yml
    assert "sak519_i" in yml

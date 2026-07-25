from __future__ import annotations

import json
from pathlib import Path

import pytest

from api.schemas.peel_responses import (
    ensure_paths_peel_503,
    list_missing_peel_503,
)

_ROOT = Path(__file__).resolve().parents[2]


# --- sak508-a: OpenAPI 503 — deploy apply + smoke ---


SAK508_A_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/platform/deploy/apply", "post"),
    ("/v1/platform/deploy/smoke", "post"),
)


@pytest.mark.sak508_a
def test_sak508_a_openapi_deploy_apply_smoke_503() -> None:
    """sak508-a: deploy apply + smoke document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK508_A_PEEL_OPENAPI:
        assert "application/problem+json" in (
            spec["paths"][path][method]["responses"]["503"]["content"]
        ), path
    assert "sak508-a" in (
        _ROOT / "packages" / "api" / "routes" / "platform_deploy_mutations.py"
    ).read_text(encoding="utf-8")


# --- sak508-b: OpenAPI 503 — deploy rollback + ci-poll ---


SAK508_B_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/platform/deploy/rollback", "post"),
    ("/v1/platform/deploy/ci-poll", "post"),
)


@pytest.mark.sak508_b
def test_sak508_b_openapi_deploy_rollback_ci_503() -> None:
    """sak508-b: deploy rollback + ci-poll document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK508_B_PEEL_OPENAPI:
        assert "application/problem+json" in (
            spec["paths"][path][method]["responses"]["503"]["content"]
        ), path
    assert "sak508-b" in (
        _ROOT / "packages" / "api" / "routes" / "platform_deploy_mutations.py"
    ).read_text(encoding="utf-8")


# --- sak508-c: OpenAPI 503 — deploy credentials GET/PUT ---


SAK508_C_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/platform/deploy/credentials", "get"),
    ("/v1/platform/deploy/credentials", "put"),
)


@pytest.mark.sak508_c
def test_sak508_c_openapi_deploy_credentials_503() -> None:
    """sak508-c: deploy credentials GET/PUT document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK508_C_PEEL_OPENAPI:
        assert "application/problem+json" in (
            spec["paths"][path][method]["responses"]["503"]["content"]
        ), path
    assert "sak508-c" in (
        _ROOT / "packages" / "api" / "routes" / "platform_deploy.py"
    ).read_text(encoding="utf-8")
    assert "sak508-c" in (
        _ROOT / "packages" / "api" / "routes" / "platform_deploy_mutations.py"
    ).read_text(encoding="utf-8")


# --- sak508-d: list_missing_peel_503 helper ---


@pytest.mark.sak508_d
def test_sak508_d_list_missing_peel_503() -> None:
    """sak508-d: list_missing_peel_503 returns pairs without mutating."""
    peel = (_ROOT / "packages" / "api" / "schemas" / "peel_responses.py").read_text(
        encoding="utf-8",
    )
    assert "sak508-d" in peel
    assert "def list_missing_peel_503" in peel
    paths = {
        "/t": {"get": {"responses": {"200": {"description": "ok"}}}},
        "/u": {"post": {"responses": {"200": {"description": "ok"}, "503": {}}}},
    }
    assert list_missing_peel_503(paths, [("/t", "get"), ("/u", "post")]) == [("/t", "get")]
    ensure_paths_peel_503(paths, [("/t", "get")])
    assert list_missing_peel_503(paths, [("/t", "get"), ("/u", "post")]) == []


# --- sak508-e: CI OpenAPI subsets ---


def test_sak508_e_ci_openapi_subsets() -> None:
    """sak508-e: peel-flag-matrix runs sak508 OpenAPI marker subsets."""
    yml = (
        _ROOT.parent / ".github" / "workflows" / "nimbusware-peel.yml"
    ).read_text(encoding="utf-8")
    assert "sak508_a" in yml
    assert "sak508_b" in yml
    assert "sak508_c" in yml
    assert "test_sak508_peel.py" in yml


# --- sak508-f: soak/CI close-out ---


def test_sak508_f_soak_and_ci_closeout() -> None:
    """sak508-f: peel_soak_lib + peel-unit list test_sak508_peel.py."""
    soak = (_ROOT / "scripts" / "peel_soak_lib.py").read_text(encoding="utf-8")
    assert "_assert_sak508_list_missing_peel" in soak
    assert "sak508-f — platform deploy OpenAPI + list_missing" in soak
    assert 'label.startswith("sak508")' in soak
    workflow = (
        _ROOT.parent / ".github" / "workflows" / "nimbusware-peel.yml"
    ).read_text(encoding="utf-8")
    peel_unit = workflow.split("  peel-unit:", 1)[1].split("  peel-flag-matrix:", 1)[0]
    assert "tests/unit/test_sak508_peel.py" in peel_unit


# --- sak508-g: OpenAPI 503 — deploy approve + terraform-validate ---


SAK508_G_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/platform/deploy/approve", "post"),
    ("/v1/platform/deploy/terraform-validate", "post"),
)


@pytest.mark.sak508_g
def test_sak508_g_openapi_deploy_approve_tf_503() -> None:
    """sak508-g: deploy approve + terraform-validate document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK508_G_PEEL_OPENAPI:
        assert "application/problem+json" in (
            spec["paths"][path][method]["responses"]["503"]["content"]
        ), path
    assert "sak508-g" in (
        _ROOT / "packages" / "api" / "routes" / "platform_deploy.py"
    ).read_text(encoding="utf-8")


# --- sak508-h: OpenAPI 503 — deploy audit + github workflow template ---


SAK508_H_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/platform/deploy/audit", "get"),
    ("/v1/platform/deploy/github-workflow-template", "get"),
)


@pytest.mark.sak508_h
def test_sak508_h_openapi_deploy_audit_template_503() -> None:
    """sak508-h: deploy audit + github-workflow-template document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK508_H_PEEL_OPENAPI:
        assert "application/problem+json" in (
            spec["paths"][path][method]["responses"]["503"]["content"]
        ), path
    assert "sak508-h" in (
        _ROOT / "packages" / "api" / "routes" / "platform_deploy.py"
    ).read_text(encoding="utf-8")


# --- sak508-i: OpenAPI 503 — platform hardware GET + rescan ---


SAK508_I_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/platform/hardware", "get"),
    ("/v1/platform/hardware/rescan", "post"),
)


@pytest.mark.sak508_i
def test_sak508_i_openapi_hardware_503() -> None:
    """sak508-i: platform hardware GET + rescan document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK508_I_PEEL_OPENAPI:
        assert "application/problem+json" in (
            spec["paths"][path][method]["responses"]["503"]["content"]
        ), path
    assert "sak508-i" in (
        _ROOT / "packages" / "api" / "routes" / "platform_hardware.py"
    ).read_text(encoding="utf-8")


# --- sak508-j: soak/CI deepen ---


def test_sak508_j_soak_and_ci_deepen() -> None:
    """sak508-j: soak deploy/hardware OpenAPI asserts + CI sak508_g/h/i markers."""
    soak = (_ROOT / "scripts" / "peel_soak_lib.py").read_text(encoding="utf-8")
    assert "_assert_sak508_deploy_hardware_openapi" in soak
    assert "sak508-j — deploy approve/audit/hardware OpenAPI" in soak
    yml = (
        _ROOT.parent / ".github" / "workflows" / "nimbusware-peel.yml"
    ).read_text(encoding="utf-8")
    assert "sak508_g" in yml
    assert "sak508_h" in yml
    assert "sak508_i" in yml

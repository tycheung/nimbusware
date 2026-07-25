from __future__ import annotations

import json
from pathlib import Path

import pytest

from api.schemas.openapi import PROBLEM_RESPONSE_503
from api.schemas.peel_responses import artifact_peel_503_response, with_enterprise_peel_503

_ROOT = Path(__file__).resolve().parents[2]


# --- sak504-a: OpenAPI 503 — auth signup/signin/signout/me ---


SAK504_A_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/auth/signup", "post"),
    ("/v1/auth/signin", "post"),
    ("/v1/auth/signout", "post"),
    ("/v1/auth/me", "get"),
)


@pytest.mark.sak504_a
def test_sak504_a_openapi_auth_503() -> None:
    """sak504-a: auth routes document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK504_A_PEEL_OPENAPI:
        assert "application/problem+json" in (
            spec["paths"][path][method]["responses"]["503"]["content"]
        ), path
    assert "sak504-a" in (
        _ROOT / "packages" / "api" / "routes" / "auth.py"
    ).read_text(encoding="utf-8")


# --- sak504-b: OpenAPI 503 — fleet autopilot + commit ---


SAK504_B_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/enterprise/tenants/{tenant_ref}/autopilot-policy", "get"),
    ("/v1/enterprise/tenants/{tenant_ref}/autopilot-policy", "put"),
    ("/v1/enterprise/tenants/{tenant_ref}/commit-policy", "get"),
    ("/v1/enterprise/tenants/{tenant_ref}/commit-policy", "put"),
)


@pytest.mark.sak504_b
def test_sak504_b_openapi_fleet_autopilot_commit_503() -> None:
    """sak504-b: autopilot + commit policy document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK504_B_PEEL_OPENAPI:
        assert "application/problem+json" in (
            spec["paths"][path][method]["responses"]["503"]["content"]
        ), path
    assert "sak504-b" in (
        _ROOT / "packages" / "api" / "routes" / "enterprise" / "fleet_autopilot.py"
    ).read_text(encoding="utf-8")
    assert "sak504-b" in (
        _ROOT / "packages" / "api" / "routes" / "enterprise" / "fleet_commit.py"
    ).read_text(encoding="utf-8")


# --- sak504-c: OpenAPI 503 — fleet deploy-approval ---


SAK504_C_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/enterprise/tenants/{tenant_ref}/deploy-approval-policy", "get"),
    ("/v1/enterprise/tenants/{tenant_ref}/deploy-approval-policy", "put"),
)


@pytest.mark.sak504_c
def test_sak504_c_openapi_deploy_approval_503() -> None:
    """sak504-c: deploy-approval policy document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK504_C_PEEL_OPENAPI:
        assert "application/problem+json" in (
            spec["paths"][path][method]["responses"]["503"]["content"]
        ), path
    assert "sak504-c" in (
        _ROOT
        / "packages"
        / "api"
        / "routes"
        / "enterprise"
        / "fleet_deploy_approval.py"
    ).read_text(encoding="utf-8")
    assert "with_enterprise_peel_503()" in (
        _ROOT
        / "packages"
        / "api"
        / "routes"
        / "enterprise"
        / "fleet_deploy_approval.py"
    ).read_text(encoding="utf-8")


# --- sak504-d: artifact_peel_503_response helper ---


@pytest.mark.sak504_d
def test_sak504_d_artifact_peel_503_response() -> None:
    """sak504-d: artifact_peel_503_response deep-copies PROBLEM_RESPONSE_503."""
    peel = (_ROOT / "packages" / "api" / "schemas" / "peel_responses.py").read_text(
        encoding="utf-8",
    )
    assert "sak504-d" in peel
    assert "def artifact_peel_503_response" in peel
    copied = artifact_peel_503_response()
    assert copied["description"] == PROBLEM_RESPONSE_503["description"]
    assert "application/problem+json" in copied["content"]
    assert copied is not PROBLEM_RESPONSE_503
    assert with_enterprise_peel_503()[503] is PROBLEM_RESPONSE_503


# --- sak504-e: CI OpenAPI subsets ---


def test_sak504_e_ci_openapi_subsets() -> None:
    """sak504-e: peel-flag-matrix runs sak504 OpenAPI marker subsets."""
    yml = (
        _ROOT.parent / ".github" / "workflows" / "nimbusware-peel.yml"
    ).read_text(encoding="utf-8")
    assert "sak504_a" in yml
    assert "sak504_b" in yml
    assert "sak504_c" in yml
    assert "test_sak504_peel.py" in yml


# --- sak504-f: soak/CI close-out ---


def test_sak504_f_soak_and_ci_closeout() -> None:
    """sak504-f: peel_soak_lib + peel-unit list test_sak504_peel.py."""
    soak = (_ROOT / "scripts" / "peel_soak_lib.py").read_text(encoding="utf-8")
    assert "_assert_sak504_artifact_peel_helper" in soak
    assert "sak504-f — auth/fleet OpenAPI + artifact_peel_503" in soak
    assert 'label.startswith("sak504")' in soak
    workflow = (
        _ROOT.parent / ".github" / "workflows" / "nimbusware-peel.yml"
    ).read_text(encoding="utf-8")
    peel_unit = workflow.split("  peel-unit:", 1)[1].split("  peel-flag-matrix:", 1)[0]
    assert "tests/unit/test_sak504_peel.py" in peel_unit


# --- sak504-g: OpenAPI 503 — timeline + findings ---


SAK504_G_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/runs/{run_id}/timeline", "get"),
    ("/v1/runs/{run_id}/findings", "get"),
)


@pytest.mark.sak504_g
def test_sak504_g_openapi_timeline_findings_503() -> None:
    """sak504-g: timeline + findings document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK504_G_PEEL_OPENAPI:
        assert "application/problem+json" in (
            spec["paths"][path][method]["responses"]["503"]["content"]
        ), path
    detail = (
        _ROOT / "packages" / "api" / "routes" / "runs" / "detail.py"
    ).read_text(encoding="utf-8")
    assert "sak504-g" in detail


# --- sak504-h: OpenAPI 503 — lifecycle plan/verify/slice ---


SAK504_H_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/runs/{run_id}/lifecycle/plan", "post"),
    ("/v1/runs/{run_id}/lifecycle/verify", "post"),
    ("/v1/runs/{run_id}/lifecycle/slice", "post"),
)


@pytest.mark.sak504_h
def test_sak504_h_openapi_lifecycle_stages_503() -> None:
    """sak504-h: lifecycle plan/verify/slice document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK504_H_PEEL_OPENAPI:
        assert "application/problem+json" in (
            spec["paths"][path][method]["responses"]["503"]["content"]
        ), path
    assert "sak504-h" in (
        _ROOT / "packages" / "api" / "routes" / "runs" / "lifecycle.py"
    ).read_text(encoding="utf-8")


# --- sak504-i: OpenAPI 503 — critic-reliability + memory-influence ---


SAK504_I_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/runs/{run_id}/critic-reliability", "get"),
    ("/v1/runs/{run_id}/memory-influence", "get"),
)


@pytest.mark.sak504_i
def test_sak504_i_openapi_critic_memory_influence_503() -> None:
    """sak504-i: critic-reliability + memory-influence document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK504_I_PEEL_OPENAPI:
        assert "application/problem+json" in (
            spec["paths"][path][method]["responses"]["503"]["content"]
        ), path
    detail = (
        _ROOT / "packages" / "api" / "routes" / "runs" / "detail.py"
    ).read_text(encoding="utf-8")
    assert "sak504-i" in detail


# --- sak504-j: soak/CI deepen ---


def test_sak504_j_soak_and_ci_deepen() -> None:
    """sak504-j: soak run projection OpenAPI asserts + CI sak504_g/h/i markers."""
    soak = (_ROOT / "scripts" / "peel_soak_lib.py").read_text(encoding="utf-8")
    assert "_assert_sak504_run_projection_openapi" in soak
    assert "sak504-j — run timeline/lifecycle/projection OpenAPI" in soak
    yml = (
        _ROOT.parent / ".github" / "workflows" / "nimbusware-peel.yml"
    ).read_text(encoding="utf-8")
    assert "sak504_g" in yml
    assert "sak504_h" in yml
    assert "sak504_i" in yml

from __future__ import annotations

import json
from pathlib import Path

import pytest

from api.schemas.peel_responses import openapi_json_peel_503_report

_ROOT = Path(__file__).resolve().parents[2]


# --- sak520-a: OpenAPI 503 — tenant model-policy GET + PUT ---


SAK520_A_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/enterprise/tenants/{tenant_ref}/model-policy", "get"),
    ("/v1/enterprise/tenants/{tenant_ref}/model-policy", "put"),
)


@pytest.mark.sak520_a
def test_sak520_a_openapi_tenant_model_policy_503() -> None:
    """sak520-a: tenant model-policy GET/PUT document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK520_A_PEEL_OPENAPI:
        assert "application/problem+json" in (
            spec["paths"][path][method]["responses"]["503"]["content"]
        ), path
    assert "sak520-a" in (
        _ROOT / "packages" / "api" / "routes" / "enterprise" / "tenant_model_policy.py"
    ).read_text(encoding="utf-8")


# --- sak520-b: OpenAPI 503 — bootstrap.json + personas overlap-report ---


SAK520_B_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/admin/app/bootstrap.json", "get"),
    ("/v1/admin/ui/personas/overlap-report", "get"),
)


@pytest.mark.sak520_b
def test_sak520_b_openapi_bootstrap_overlap_503() -> None:
    """sak520-b: bootstrap.json + personas overlap-report document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK520_B_PEEL_OPENAPI:
        assert "application/problem+json" in (
            spec["paths"][path][method]["responses"]["503"]["content"]
        ), path
    assert "sak520-b" in (
        _ROOT / "packages" / "api" / "routes" / "web_bootstrap.py"
    ).read_text(encoding="utf-8")
    assert "sak520-b" in (
        _ROOT / "packages" / "api" / "routes" / "admin_ui_bff.py"
    ).read_text(encoding="utf-8")


# --- sak520-c: OpenAPI 503 — fleet-autopilot-policy admin-ui GET + PUT ---


SAK520_C_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/admin/ui/enterprise/fleet-autopilot-policy", "get"),
    ("/v1/admin/ui/enterprise/fleet-autopilot-policy", "put"),
)


@pytest.mark.sak520_c
def test_sak520_c_openapi_fleet_autopilot_admin_ui_503() -> None:
    """sak520-c: admin-ui fleet-autopilot-policy GET/PUT document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK520_C_PEEL_OPENAPI:
        assert "application/problem+json" in (
            spec["paths"][path][method]["responses"]["503"]["content"]
        ), path
    assert "sak520-c" in (
        _ROOT / "packages" / "api" / "routes" / "admin_ui_bff.py"
    ).read_text(encoding="utf-8")


# --- sak520-d: openapi_json_peel_503_report helper ---


@pytest.mark.sak520_d
def test_sak520_d_openapi_json_peel_503_report(tmp_path: Path) -> None:
    """sak520-d: openapi_json_peel_503_report returns complete/missing/count."""
    peel = (_ROOT / "packages" / "api" / "schemas" / "peel_responses.py").read_text(
        encoding="utf-8",
    )
    assert "sak520-d" in peel
    assert "openapi_json_peel_503_report" in peel
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
    ok = openapi_json_peel_503_report(path, [("/t", "get")])
    assert ok["complete"] is True
    assert ok["count"] == 0
    assert ok["missing"] == []
    bad = openapi_json_peel_503_report(path, [("/t", "get"), ("/u", "post")])
    assert bad["complete"] is False
    assert bad["count"] == 1
    assert bad["missing"] == [("/u", "post")]


# --- sak520-e: CI OpenAPI subsets ---


def test_sak520_e_ci_openapi_subsets() -> None:
    """sak520-e: peel-flag-matrix runs sak520 OpenAPI marker subsets."""
    yml = (
        _ROOT.parent / ".github" / "workflows" / "nimbusware-peel.yml"
    ).read_text(encoding="utf-8")
    assert "sak520_a" in yml
    assert "sak520_b" in yml
    assert "sak520_c" in yml
    assert "test_sak520_peel.py" in yml


# --- sak520-f: soak/CI close-out ---


def test_sak520_f_soak_and_ci_closeout() -> None:
    """sak520-f: peel_soak_lib + peel-unit list test_sak520_peel.py."""
    soak = (_ROOT / "scripts" / "peel_soak_lib.py").read_text(encoding="utf-8")
    assert "_assert_sak520_report_helper" in soak
    assert "sak520-f — tenant model-policy/bootstrap OpenAPI + report helper" in soak
    assert 'label.startswith("sak520")' in soak
    workflow = (
        _ROOT.parent / ".github" / "workflows" / "nimbusware-peel.yml"
    ).read_text(encoding="utf-8")
    peel_unit = workflow.split("  peel-unit:", 1)[1].split("  peel-flag-matrix:", 1)[0]
    assert "tests/unit/test_sak520_peel.py" in peel_unit


# --- sak520-g: OpenAPI 503 — fleet-enforcement-policy GET ---


SAK520_G_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/admin/ui/enterprise/fleet-enforcement-policy", "get"),
)


@pytest.mark.sak520_g
def test_sak520_g_openapi_fleet_enforcement_get_503() -> None:
    """sak520-g: admin-ui fleet-enforcement-policy GET documents 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK520_G_PEEL_OPENAPI:
        assert "application/problem+json" in (
            spec["paths"][path][method]["responses"]["503"]["content"]
        ), path
    assert "sak520-g" in (
        _ROOT / "packages" / "api" / "routes" / "admin_ui_bff.py"
    ).read_text(encoding="utf-8")


# --- sak520-h: OpenAPI 503 — fleet-enforcement-policy PUT ---


SAK520_H_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/admin/ui/enterprise/fleet-enforcement-policy", "put"),
)


@pytest.mark.sak520_h
def test_sak520_h_openapi_fleet_enforcement_put_503() -> None:
    """sak520-h: admin-ui fleet-enforcement-policy PUT documents 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK520_H_PEEL_OPENAPI:
        assert "application/problem+json" in (
            spec["paths"][path][method]["responses"]["503"]["content"]
        ), path
    assert "sak520-h" in (
        _ROOT / "packages" / "api" / "routes" / "admin_ui_bff.py"
    ).read_text(encoding="utf-8")


# --- sak520-i: OpenAPI 503 — maker push-subscriptions POST + DELETE ---


SAK520_I_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/maker/push-subscriptions", "post"),
    ("/v1/maker/push-subscriptions", "delete"),
)


@pytest.mark.sak520_i
def test_sak520_i_openapi_push_subscriptions_mutate_503() -> None:
    """sak520-i: maker push-subscriptions POST/DELETE document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK520_I_PEEL_OPENAPI:
        assert "application/problem+json" in (
            spec["paths"][path][method]["responses"]["503"]["content"]
        ), path
    assert "sak520-i" in (
        _ROOT / "packages" / "api" / "routes" / "maker_push.py"
    ).read_text(encoding="utf-8")


# --- sak520-j: soak/CI deepen ---


def test_sak520_j_soak_and_ci_deepen() -> None:
    """sak520-j: soak/CI cover enforcement/push OpenAPI deepen."""
    soak = (_ROOT / "scripts" / "peel_soak_lib.py").read_text(encoding="utf-8")
    assert "_assert_sak520_enforcement_push_openapi" in soak
    assert "sak520-j — enforcement/push OpenAPI" in soak
    yml = (
        _ROOT.parent / ".github" / "workflows" / "nimbusware-peel.yml"
    ).read_text(encoding="utf-8")
    assert "sak520_g" in yml
    assert "sak520_h" in yml
    assert "sak520_i" in yml

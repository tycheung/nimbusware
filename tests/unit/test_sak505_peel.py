from __future__ import annotations

import json
from pathlib import Path

import pytest

from api.schemas.peel_responses import (
    artifact_peel_503_response,
    ensure_operation_peel_503,
)

_ROOT = Path(__file__).resolve().parents[2]


# --- sak505-a: OpenAPI 503 — personas list + overlap-report ---


SAK505_A_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/personas", "get"),
    ("/v1/personas/overlap-report", "get"),
)


@pytest.mark.sak505_a
def test_sak505_a_openapi_personas_503() -> None:
    """sak505-a: personas list + overlap-report document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK505_A_PEEL_OPENAPI:
        assert "application/problem+json" in (
            spec["paths"][path][method]["responses"]["503"]["content"]
        ), path
    assert "sak505-a" in (
        _ROOT / "packages" / "api" / "routes" / "personas_handlers.py"
    ).read_text(encoding="utf-8")


# --- sak505-b: OpenAPI 503 — bundles search + scraper inventory ---


SAK505_B_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/bundles/search", "get"),
    ("/v1/scraper-artifacts/inventory", "get"),
)


@pytest.mark.sak505_b
def test_sak505_b_openapi_bundles_scraper_503() -> None:
    """sak505-b: bundles search + scraper inventory document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK505_B_PEEL_OPENAPI:
        assert "application/problem+json" in (
            spec["paths"][path][method]["responses"]["503"]["content"]
        ), path
    assert "sak505-b" in (
        _ROOT / "packages" / "api" / "routes" / "bundles_search.py"
    ).read_text(encoding="utf-8")
    assert "sak505-b" in (
        _ROOT / "packages" / "api" / "routes" / "scraper_artifacts.py"
    ).read_text(encoding="utf-8")


# --- sak505-c: OpenAPI 503 — blast-radius + critic-pack detail ---


SAK505_C_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/config/blast-radius", "get"),
    ("/v1/config/critic-packs/{pack_id}", "get"),
    ("/v1/config/critic-packs/{pack_id}/workflows", "get"),
)


@pytest.mark.sak505_c
def test_sak505_c_openapi_blast_critic_detail_503() -> None:
    """sak505-c: blast-radius + critic-pack detail/workflows document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK505_C_PEEL_OPENAPI:
        assert "application/problem+json" in (
            spec["paths"][path][method]["responses"]["503"]["content"]
        ), path
    assert "sak505-c" in (
        _ROOT / "packages" / "api" / "routes" / "config_ops.py"
    ).read_text(encoding="utf-8")
    assert "sak505-c" in (
        _ROOT / "packages" / "api" / "routes" / "critic_packs.py"
    ).read_text(encoding="utf-8")


# --- sak505-d: ensure_operation_peel_503 helper ---


@pytest.mark.sak505_d
def test_sak505_d_ensure_operation_peel_503() -> None:
    """sak505-d: ensure_operation_peel_503 inserts once and is idempotent."""
    peel = (_ROOT / "packages" / "api" / "schemas" / "peel_responses.py").read_text(
        encoding="utf-8",
    )
    assert "sak505-d" in peel
    assert "def ensure_operation_peel_503" in peel
    op: dict = {"responses": {"200": {"description": "ok"}}}
    assert ensure_operation_peel_503(op) is True
    assert op["responses"]["503"]["description"] == artifact_peel_503_response()[
        "description"
    ]
    assert ensure_operation_peel_503(op) is False


# --- sak505-e: CI OpenAPI subsets ---


def test_sak505_e_ci_openapi_subsets() -> None:
    """sak505-e: peel-flag-matrix runs sak505 OpenAPI marker subsets."""
    yml = (
        _ROOT.parent / ".github" / "workflows" / "nimbusware-peel.yml"
    ).read_text(encoding="utf-8")
    assert "sak505_a" in yml
    assert "sak505_b" in yml
    assert "sak505_c" in yml
    assert "test_sak505_peel.py" in yml


# --- sak505-f: soak/CI close-out ---


def test_sak505_f_soak_and_ci_closeout() -> None:
    """sak505-f: peel_soak_lib + peel-unit list test_sak505_peel.py."""
    soak = (_ROOT / "scripts" / "peel_soak_lib.py").read_text(encoding="utf-8")
    assert "_assert_sak505_ensure_operation_peel" in soak
    assert "sak505-f — personas/bundles/config OpenAPI + ensure_operation" in soak
    assert 'label.startswith("sak505")' in soak
    workflow = (
        _ROOT.parent / ".github" / "workflows" / "nimbusware-peel.yml"
    ).read_text(encoding="utf-8")
    peel_unit = workflow.split("  peel-unit:", 1)[1].split("  peel-flag-matrix:", 1)[0]
    assert "tests/unit/test_sak505_peel.py" in peel_unit


# --- sak505-g: OpenAPI 503 — model-bindings swap + audit ---


SAK505_G_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/runs/{run_id}/model-bindings/swap", "post"),
    ("/v1/runs/{run_id}/model-bindings/audit", "get"),
)


@pytest.mark.sak505_g
def test_sak505_g_openapi_model_bindings_503() -> None:
    """sak505-g: model-bindings swap + audit document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK505_G_PEEL_OPENAPI:
        assert "application/problem+json" in (
            spec["paths"][path][method]["responses"]["503"]["content"]
        ), path
    src = (
        _ROOT / "packages" / "api" / "routes" / "runs" / "model_bindings_swap.py"
    ).read_text(encoding="utf-8")
    assert "sak505-g" in src


# --- sak505-h: OpenAPI 503 — role-claims POST/DELETE ---


SAK505_H_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/runs/{run_id}/role-claims", "post"),
    ("/v1/runs/{run_id}/role-claims/{agent_role}", "delete"),
)


@pytest.mark.sak505_h
def test_sak505_h_openapi_role_claims_503() -> None:
    """sak505-h: role-claims POST/DELETE document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK505_H_PEEL_OPENAPI:
        assert "application/problem+json" in (
            spec["paths"][path][method]["responses"]["503"]["content"]
        ), path
    src = (
        _ROOT / "packages" / "api" / "routes" / "runs" / "model_bindings_swap.py"
    ).read_text(encoding="utf-8")
    assert "sak505-h" in src


# --- sak505-i: OpenAPI 503 — autopilot/enforcement PUT ---


SAK505_I_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/runs/{run_id}/autopilot", "put"),
    ("/v1/runs/{run_id}/enforcement", "put"),
)


@pytest.mark.sak505_i
def test_sak505_i_openapi_autopilot_enforcement_put_503() -> None:
    """sak505-i: autopilot/enforcement PUT document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK505_I_PEEL_OPENAPI:
        assert "application/problem+json" in (
            spec["paths"][path][method]["responses"]["503"]["content"]
        ), path
    assert "sak505-i" in (
        _ROOT / "packages" / "api" / "routes" / "runs" / "autopilot.py"
    ).read_text(encoding="utf-8")
    assert "sak505-i" in (
        _ROOT / "packages" / "api" / "routes" / "runs" / "enforcement.py"
    ).read_text(encoding="utf-8")


# --- sak505-j: soak/CI deepen ---


def test_sak505_j_soak_and_ci_deepen() -> None:
    """sak505-j: soak binding/autopilot OpenAPI asserts + CI sak505_g/h/i markers."""
    soak = (_ROOT / "scripts" / "peel_soak_lib.py").read_text(encoding="utf-8")
    assert "_assert_sak505_bindings_autopilot_openapi" in soak
    assert "sak505-j — bindings/role-claims/autopilot OpenAPI" in soak
    yml = (
        _ROOT.parent / ".github" / "workflows" / "nimbusware-peel.yml"
    ).read_text(encoding="utf-8")
    assert "sak505_g" in yml
    assert "sak505_h" in yml
    assert "sak505_i" in yml

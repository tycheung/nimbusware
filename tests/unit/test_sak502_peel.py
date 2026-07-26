from __future__ import annotations

import json
from pathlib import Path

import pytest

from api.schemas.openapi import PROBLEM_RESPONSE_503
from api.schemas.peel_responses import (
    long_tail_json_openapi_responses,
    with_long_tail_peel_503,
)

_ROOT = Path(__file__).resolve().parents[2]


# --- sak502-a: OpenAPI 503 — runs create/list ---


SAK502_A_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/runs", "post"),
    ("/v1/runs", "get"),
)


@pytest.mark.sak502_a
def test_sak502_a_openapi_runs_create_list_503() -> None:
    """sak502-a: POST/GET /runs document 503 via with_long_tail_peel_503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK502_A_PEEL_OPENAPI:
        assert (
            "application/problem+json"
            in (spec["paths"][path][method]["responses"]["503"]["content"])
        ), f"{method} {path}"
    create = (_ROOT / "packages" / "api" / "routes" / "runs" / "create.py").read_text(
        encoding="utf-8",
    )
    listing = (_ROOT / "packages" / "api" / "routes" / "runs" / "list.py").read_text(
        encoding="utf-8",
    )
    assert "sak502-a" in create and "with_long_tail_peel_503" in create
    assert "sak502-a" in listing and "with_long_tail_peel_503" in listing


# --- sak502-b: OpenAPI 503 — provider presets/connections ---


SAK502_B_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/platform/provider-presets", "get"),
    ("/v1/platform/provider-connections", "get"),
)


@pytest.mark.sak502_b
def test_sak502_b_openapi_provider_503() -> None:
    """sak502-b: provider presets/connections document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK502_B_PEEL_OPENAPI:
        assert (
            "application/problem+json"
            in (spec["paths"][path][method]["responses"]["503"]["content"])
        ), path
    src = (_ROOT / "packages" / "api" / "routes" / "provider_connections.py").read_text(
        encoding="utf-8"
    )
    assert src.count("sak502-b") >= 2


# --- sak502-c: OpenAPI 503 — fleet deploy/discovery policies ---


SAK502_C_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/enterprise/tenants/{tenant_ref}/deploy-policy", "get"),
    ("/v1/enterprise/tenants/{tenant_ref}/discovery-policy", "get"),
)


@pytest.mark.sak502_c
def test_sak502_c_openapi_fleet_policies_503() -> None:
    """sak502-c: enterprise deploy/discovery policy GETs document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK502_C_PEEL_OPENAPI:
        assert (
            "application/problem+json"
            in (spec["paths"][path][method]["responses"]["503"]["content"])
        ), path
    deploy = (_ROOT / "packages" / "api" / "routes" / "enterprise" / "fleet_deploy.py").read_text(
        encoding="utf-8"
    )
    discovery = (
        _ROOT / "packages" / "api" / "routes" / "enterprise" / "fleet_discovery.py"
    ).read_text(encoding="utf-8")
    assert "sak502-c" in deploy
    assert "sak502-c" in discovery


# --- sak502-d: with_long_tail_peel_503 helper ---


@pytest.mark.sak502_d
def test_sak502_d_with_long_tail_peel_503_merges() -> None:
    """sak502-d: with_long_tail_peel_503 merges 503 into existing responses."""
    peel = (_ROOT / "packages" / "api" / "schemas" / "peel_responses.py").read_text(
        encoding="utf-8",
    )
    assert "sak502-d" in peel
    assert "def with_long_tail_peel_503" in peel
    merged = with_long_tail_peel_503({200: {"description": "ok"}, 422: {"description": "bad"}})
    assert merged[200]["description"] == "ok"
    assert merged[422]["description"] == "bad"
    assert merged[503] is PROBLEM_RESPONSE_503
    assert long_tail_json_openapi_responses()[503] is PROBLEM_RESPONSE_503


# --- sak502-e: CI OpenAPI subsets ---


def test_sak502_e_ci_openapi_subsets() -> None:
    """sak502-e: peel-flag-matrix runs sak502 OpenAPI marker subsets."""
    yml = (_ROOT.parent / ".github" / "workflows" / "nimbusware-peel.yml").read_text(
        encoding="utf-8"
    )
    assert "sak502_a" in yml
    assert "sak502_b" in yml
    assert "sak502_c" in yml
    assert "test_sak502_peel.py" in yml


# --- sak502-f: soak/CI close-out ---


def test_sak502_f_soak_and_ci_closeout() -> None:
    """sak502-f: peel_soak_lib + peel-unit list test_sak502_peel.py."""
    soak = (_ROOT / "scripts" / "peel_soak_lib.py").read_text(encoding="utf-8")
    assert "_assert_sak502_with_long_tail_helper" in soak
    assert "sak502-f — runs/provider/fleet OpenAPI" in soak
    assert 'label.startswith("sak502")' in soak
    workflow = (_ROOT.parent / ".github" / "workflows" / "nimbusware-peel.yml").read_text(
        encoding="utf-8"
    )
    peel_unit = workflow.split("  peel-unit:", 1)[1].split("  peel-flag-matrix:", 1)[0]
    assert "tests/unit/test_sak502_peel.py" in peel_unit


# --- sak502-g: OpenAPI 503 — run detail + lifecycle start ---


SAK502_G_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/runs/{run_id}", "get"),
    ("/v1/runs/{run_id}/lifecycle/start", "post"),
)


@pytest.mark.sak502_g
def test_sak502_g_openapi_run_detail_lifecycle_503() -> None:
    """sak502-g: run detail + lifecycle/start document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK502_G_PEEL_OPENAPI:
        assert (
            "application/problem+json"
            in (spec["paths"][path][method]["responses"]["503"]["content"])
        ), f"{method} {path}"
    detail = (_ROOT / "packages" / "api" / "routes" / "runs" / "detail.py").read_text(
        encoding="utf-8",
    )
    life = (_ROOT / "packages" / "api" / "routes" / "runs" / "lifecycle.py").read_text(
        encoding="utf-8",
    )
    assert "sak502-g" in detail and "with_long_tail_peel_503" in detail
    assert "sak502-g" in life


# --- sak502-h: OpenAPI 503 — slice diff + stitch-summary ---


SAK502_H_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/runs/{run_id}/slices/{slice_index}/diff", "get"),
    ("/v1/runs/{run_id}/stitch-summary", "get"),
)


@pytest.mark.sak502_h
def test_sak502_h_openapi_slice_stitch_503() -> None:
    """sak502-h: slice diff + stitch-summary document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK502_H_PEEL_OPENAPI:
        assert (
            "application/problem+json"
            in (spec["paths"][path][method]["responses"]["503"]["content"])
        ), path
    assert "sak502-h" in (_ROOT / "packages" / "api" / "routes" / "runs" / "slices.py").read_text(
        encoding="utf-8"
    )
    assert "sak502-h" in (
        _ROOT / "packages" / "api" / "routes" / "runs" / "stitch_summary.py"
    ).read_text(encoding="utf-8")


# --- sak502-i: OpenAPI 503 — factory-evidence + timeline explain ---


SAK502_I_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/runs/{run_id}/factory-evidence", "get"),
    ("/v1/runs/{run_id}/timeline/{section}/explain", "get"),
)


@pytest.mark.sak502_i
def test_sak502_i_openapi_factory_timeline_503() -> None:
    """sak502-i: factory-evidence + timeline explain document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK502_I_PEEL_OPENAPI:
        assert (
            "application/problem+json"
            in (spec["paths"][path][method]["responses"]["503"]["content"])
        ), path
    assert "sak502-i" in (
        _ROOT / "packages" / "api" / "routes" / "runs" / "factory_evidence.py"
    ).read_text(encoding="utf-8")
    assert "sak502-i" in (
        _ROOT / "packages" / "api" / "routes" / "runs" / "timeline_explain.py"
    ).read_text(encoding="utf-8")


# --- sak502-j: deepen close-out g–i ---


def test_sak502_j_soak_and_ci_deepen() -> None:
    """sak502-j: soak run OpenAPI asserts + CI sak502_g/h/i markers."""
    soak = (_ROOT / "scripts" / "peel_soak_lib.py").read_text(encoding="utf-8")
    assert "_assert_sak502_run_detail_openapi" in soak
    assert "sak502-j — run detail/slice/factory OpenAPI" in soak
    yml = (_ROOT.parent / ".github" / "workflows" / "nimbusware-peel.yml").read_text(
        encoding="utf-8"
    )
    assert "sak502_g" in yml
    assert "sak502_h" in yml
    assert "sak502_i" in yml

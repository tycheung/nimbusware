from __future__ import annotations

import json
from pathlib import Path

import pytest

from api.schemas.peel_responses import count_missing_peel_503, ensure_paths_peel_503

_ROOT = Path(__file__).resolve().parents[2]


# --- sak507-a: OpenAPI 503 — maker pending + git-status ---


SAK507_A_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/runs/{run_id}/maker/git-status", "get"),
    ("/v1/runs/{run_id}/maker/pending", "get"),
)


@pytest.mark.sak507_a
def test_sak507_a_openapi_maker_status_503() -> None:
    """sak507-a: maker git-status + pending document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK507_A_PEEL_OPENAPI:
        assert (
            "application/problem+json"
            in (spec["paths"][path][method]["responses"]["503"]["content"])
        ), path
    assert "sak507-a" in (
        _ROOT / "packages" / "api" / "routes" / "runs" / "maker_approval.py"
    ).read_text(encoding="utf-8")


# --- sak507-b: OpenAPI 503 — maker plan approve + slices prepare ---


SAK507_B_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/runs/{run_id}/maker/plan/approve", "post"),
    ("/v1/runs/{run_id}/maker/slices/prepare", "post"),
)


@pytest.mark.sak507_b
def test_sak507_b_openapi_maker_plan_prepare_503() -> None:
    """sak507-b: maker plan approve + slices prepare document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK507_B_PEEL_OPENAPI:
        assert (
            "application/problem+json"
            in (spec["paths"][path][method]["responses"]["503"]["content"])
        ), path
    assert "sak507-b" in (
        _ROOT / "packages" / "api" / "routes" / "runs" / "maker_approval.py"
    ).read_text(encoding="utf-8")


# --- sak507-c: OpenAPI 503 — user standards-profile ---


SAK507_C_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/users/me/standards-profile", "get"),
    ("/v1/users/me/standards-profile/{profile_id}", "put"),
)


@pytest.mark.sak507_c
def test_sak507_c_openapi_standards_profile_503() -> None:
    """sak507-c: user standards-profile GET/PUT document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK507_C_PEEL_OPENAPI:
        assert (
            "application/problem+json"
            in (spec["paths"][path][method]["responses"]["503"]["content"])
        ), path
    assert "sak507-c" in (_ROOT / "packages" / "api" / "routes" / "standards.py").read_text(
        encoding="utf-8"
    )


# --- sak507-d: count_missing_peel_503 helper ---


@pytest.mark.sak507_d
def test_sak507_d_count_missing_peel_503() -> None:
    """sak507-d: count_missing_peel_503 inventories without mutating."""
    peel = (_ROOT / "packages" / "api" / "schemas" / "peel_responses.py").read_text(
        encoding="utf-8",
    )
    assert "sak507-d" in peel
    assert "def count_missing_peel_503" in peel
    paths = {
        "/t": {"get": {"responses": {"200": {"description": "ok"}}}},
        "/u": {"post": {"responses": {"200": {"description": "ok"}, "503": {}}}},
    }
    assert count_missing_peel_503(paths, [("/t", "get"), ("/u", "post")]) == 1
    assert count_missing_peel_503(paths, [("/missing", "get")]) == 1
    ensure_paths_peel_503(paths, [("/t", "get")])
    assert count_missing_peel_503(paths, [("/t", "get"), ("/u", "post")]) == 0


# --- sak507-e: CI OpenAPI subsets ---


def test_sak507_e_ci_openapi_subsets() -> None:
    """sak507-e: peel-flag-matrix runs sak507 OpenAPI marker subsets."""
    yml = (_ROOT.parent / ".github" / "workflows" / "nimbusware-peel.yml").read_text(
        encoding="utf-8"
    )
    assert "sak507_a" in yml
    assert "sak507_b" in yml
    assert "sak507_c" in yml
    assert "test_sak507_peel.py" in yml


# --- sak507-f: soak/CI close-out ---


def test_sak507_f_soak_and_ci_closeout() -> None:
    """sak507-f: peel_soak_lib + peel-unit list test_sak507_peel.py."""
    soak = (_ROOT / "scripts" / "peel_soak_lib.py").read_text(encoding="utf-8")
    assert "_assert_sak507_count_missing_peel" in soak
    assert "sak507-f — maker/standards-profile OpenAPI + count_missing" in soak
    assert 'label.startswith("sak507")' in soak
    workflow = (_ROOT.parent / ".github" / "workflows" / "nimbusware-peel.yml").read_text(
        encoding="utf-8"
    )
    peel_unit = workflow.split("  peel-unit:", 1)[1].split("  peel-flag-matrix:", 1)[0]
    assert "tests/unit/test_sak507_peel.py" in peel_unit


# --- sak507-g: OpenAPI 503 — maker open-pr + slices apply ---


SAK507_G_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/runs/{run_id}/maker/open-pr", "post"),
    ("/v1/runs/{run_id}/maker/slices/apply", "post"),
)


@pytest.mark.sak507_g
def test_sak507_g_openapi_maker_open_apply_503() -> None:
    """sak507-g: maker open-pr + slices apply document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK507_G_PEEL_OPENAPI:
        assert (
            "application/problem+json"
            in (spec["paths"][path][method]["responses"]["503"]["content"])
        ), path
    assert "sak507-g" in (
        _ROOT / "packages" / "api" / "routes" / "runs" / "maker_approval.py"
    ).read_text(encoding="utf-8")


# --- sak507-h: OpenAPI 503 — maker skip + workspace revert ---


SAK507_H_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/runs/{run_id}/maker/slices/skip", "post"),
    ("/v1/runs/{run_id}/workspace/revert", "post"),
)


@pytest.mark.sak507_h
def test_sak507_h_openapi_maker_skip_revert_503() -> None:
    """sak507-h: maker slices skip + workspace revert document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK507_H_PEEL_OPENAPI:
        assert (
            "application/problem+json"
            in (spec["paths"][path][method]["responses"]["503"]["content"])
        ), path
    assert "sak507-h" in (
        _ROOT / "packages" / "api" / "routes" / "runs" / "maker_approval.py"
    ).read_text(encoding="utf-8")


# --- sak507-i: OpenAPI 503 — maker run-tests + campaign artifact bundle ---


SAK507_I_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/runs/{run_id}/maker/run-tests", "post"),
    ("/v1/runs/{run_id}/campaign-artifact-bundle", "get"),
)


@pytest.mark.sak507_i
def test_sak507_i_openapi_maker_tests_bundle_503() -> None:
    """sak507-i: maker run-tests + campaign-artifact-bundle document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK507_I_PEEL_OPENAPI:
        assert (
            "application/problem+json"
            in (spec["paths"][path][method]["responses"]["503"]["content"])
        ), path
    assert "sak507-i" in (
        _ROOT / "packages" / "api" / "routes" / "runs" / "maker_approval.py"
    ).read_text(encoding="utf-8")
    assert "sak507-i" in (
        _ROOT / "packages" / "api" / "routes" / "runs" / "artifact_bundle.py"
    ).read_text(encoding="utf-8")


# --- sak507-j: soak/CI deepen ---


def test_sak507_j_soak_and_ci_deepen() -> None:
    """sak507-j: soak maker mutate OpenAPI asserts + CI sak507_g/h/i markers."""
    soak = (_ROOT / "scripts" / "peel_soak_lib.py").read_text(encoding="utf-8")
    assert "_assert_sak507_maker_mutate_openapi" in soak
    assert "sak507-j — maker mutate/bundle OpenAPI" in soak
    yml = (_ROOT.parent / ".github" / "workflows" / "nimbusware-peel.yml").read_text(
        encoding="utf-8"
    )
    assert "sak507_g" in yml
    assert "sak507_h" in yml
    assert "sak507_i" in yml

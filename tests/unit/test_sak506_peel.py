from __future__ import annotations

import json
from pathlib import Path

import pytest

from api.schemas.peel_responses import ensure_paths_peel_503

_ROOT = Path(__file__).resolve().parents[2]


# --- sak506-a: OpenAPI 503 — theater GET + export ---


SAK506_A_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/runs/{run_id}/theater", "get"),
    ("/v1/runs/{run_id}/theater/export", "get"),
)


@pytest.mark.sak506_a
def test_sak506_a_openapi_theater_503() -> None:
    """sak506-a: theater GET + export document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK506_A_PEEL_OPENAPI:
        assert "application/problem+json" in (
            spec["paths"][path][method]["responses"]["503"]["content"]
        ), path
    assert "sak506-a" in (
        _ROOT / "packages" / "api" / "routes" / "runs" / "theater.py"
    ).read_text(encoding="utf-8")


# --- sak506-b: OpenAPI 503 — actions retry + escalate ---


SAK506_B_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/runs/{run_id}/actions/retry", "post"),
    ("/v1/runs/{run_id}/actions/escalate", "post"),
)


@pytest.mark.sak506_b
def test_sak506_b_openapi_actions_503() -> None:
    """sak506-b: actions retry + escalate document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK506_B_PEEL_OPENAPI:
        assert "application/problem+json" in (
            spec["paths"][path][method]["responses"]["503"]["content"]
        ), path
    assert "sak506-b" in (
        _ROOT / "packages" / "api" / "routes" / "actions.py"
    ).read_text(encoding="utf-8")


# --- sak506-c: OpenAPI 503 — run standards GET + report ---


SAK506_C_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/runs/{run_id}/standards", "get"),
    ("/v1/runs/{run_id}/standards/report", "get"),
)


@pytest.mark.sak506_c
def test_sak506_c_openapi_run_standards_503() -> None:
    """sak506-c: run standards GET + report document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK506_C_PEEL_OPENAPI:
        assert "application/problem+json" in (
            spec["paths"][path][method]["responses"]["503"]["content"]
        ), path
    assert "sak506-c" in (
        _ROOT / "packages" / "api" / "routes" / "standards.py"
    ).read_text(encoding="utf-8")


# --- sak506-d: ensure_paths_peel_503 helper ---


@pytest.mark.sak506_d
def test_sak506_d_ensure_paths_peel_503() -> None:
    """sak506-d: ensure_paths_peel_503 batch-inserts once then returns 0."""
    peel = (_ROOT / "packages" / "api" / "schemas" / "peel_responses.py").read_text(
        encoding="utf-8",
    )
    assert "sak506-d" in peel
    assert "def ensure_paths_peel_503" in peel
    paths = {
        "/t": {"get": {"responses": {"200": {"description": "ok"}}}},
        "/u": {"post": {"responses": {"200": {"description": "ok"}}}},
    }
    assert ensure_paths_peel_503(paths, [("/t", "get"), ("/u", "post")]) == 2
    assert "503" in paths["/t"]["get"]["responses"]
    assert ensure_paths_peel_503(paths, [("/t", "get"), ("/u", "post")]) == 0


# --- sak506-e: CI OpenAPI subsets ---


def test_sak506_e_ci_openapi_subsets() -> None:
    """sak506-e: peel-flag-matrix runs sak506 OpenAPI marker subsets."""
    yml = (
        _ROOT.parent / ".github" / "workflows" / "nimbusware-peel.yml"
    ).read_text(encoding="utf-8")
    assert "sak506_a" in yml
    assert "sak506_b" in yml
    assert "sak506_c" in yml
    assert "test_sak506_peel.py" in yml


# --- sak506-f: soak/CI close-out ---


def test_sak506_f_soak_and_ci_closeout() -> None:
    """sak506-f: peel_soak_lib + peel-unit list test_sak506_peel.py."""
    soak = (_ROOT / "scripts" / "peel_soak_lib.py").read_text(encoding="utf-8")
    assert "_assert_sak506_ensure_paths_peel" in soak
    assert "sak506-f — theater/actions/standards OpenAPI + ensure_paths" in soak
    assert 'label.startswith("sak506")' in soak
    workflow = (
        _ROOT.parent / ".github" / "workflows" / "nimbusware-peel.yml"
    ).read_text(encoding="utf-8")
    peel_unit = workflow.split("  peel-unit:", 1)[1].split("  peel-flag-matrix:", 1)[0]
    assert "tests/unit/test_sak506_peel.py" in peel_unit


# --- sak506-g: OpenAPI 503 — override-gate + interjection POST ---


SAK506_G_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/runs/{run_id}/actions/override-gate", "post"),
    ("/v1/runs/{run_id}/interjection-queue", "post"),
)


@pytest.mark.sak506_g
def test_sak506_g_openapi_override_interjection_503() -> None:
    """sak506-g: override-gate + interjection POST document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK506_G_PEEL_OPENAPI:
        assert "application/problem+json" in (
            spec["paths"][path][method]["responses"]["503"]["content"]
        ), path
    assert "sak506-g" in (
        _ROOT / "packages" / "api" / "routes" / "actions.py"
    ).read_text(encoding="utf-8")
    assert "sak506-g" in (
        _ROOT / "packages" / "api" / "routes" / "runs" / "interjection.py"
    ).read_text(encoding="utf-8")


# --- sak506-h: OpenAPI 503 — standards presets + defaults ---


SAK506_H_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/standards/presets/{preset_id}", "get"),
    ("/v1/standards/presets/{preset_id}/defaults", "get"),
)


@pytest.mark.sak506_h
def test_sak506_h_openapi_standards_presets_503() -> None:
    """sak506-h: standards presets + defaults document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK506_H_PEEL_OPENAPI:
        assert "application/problem+json" in (
            spec["paths"][path][method]["responses"]["503"]["content"]
        ), path
    assert "sak506-h" in (
        _ROOT / "packages" / "api" / "routes" / "standards.py"
    ).read_text(encoding="utf-8")


# --- sak506-i: OpenAPI 503 — standards PUT + run ---


SAK506_I_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/runs/{run_id}/standards", "put"),
    ("/v1/runs/{run_id}/standards/run", "post"),
)


@pytest.mark.sak506_i
def test_sak506_i_openapi_standards_mutate_503() -> None:
    """sak506-i: standards PUT + run document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK506_I_PEEL_OPENAPI:
        assert "application/problem+json" in (
            spec["paths"][path][method]["responses"]["503"]["content"]
        ), path
    assert "sak506-i" in (
        _ROOT / "packages" / "api" / "routes" / "standards.py"
    ).read_text(encoding="utf-8")


# --- sak506-j: soak/CI deepen ---


def test_sak506_j_soak_and_ci_deepen() -> None:
    """sak506-j: soak standards/actions OpenAPI asserts + CI sak506_g/h/i markers."""
    soak = (_ROOT / "scripts" / "peel_soak_lib.py").read_text(encoding="utf-8")
    assert "_assert_sak506_standards_actions_openapi" in soak
    assert "sak506-j — override/interjection/standards OpenAPI" in soak
    yml = (
        _ROOT.parent / ".github" / "workflows" / "nimbusware-peel.yml"
    ).read_text(encoding="utf-8")
    assert "sak506_g" in yml
    assert "sak506_h" in yml
    assert "sak506_i" in yml

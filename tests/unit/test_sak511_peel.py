from __future__ import annotations

import json
from pathlib import Path

import pytest

from api.schemas.peel_responses import openapi_peel_503_complete

_ROOT = Path(__file__).resolve().parents[2]


# --- sak511-a: OpenAPI 503 — enterprise status + health ---


SAK511_A_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/enterprise/status", "get"),
    ("/v1/enterprise/health", "get"),
)


@pytest.mark.sak511_a
def test_sak511_a_openapi_enterprise_status_health_503() -> None:
    """sak511-a: enterprise status + health document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK511_A_PEEL_OPENAPI:
        assert "application/problem+json" in (
            spec["paths"][path][method]["responses"]["503"]["content"]
        ), path
    assert "sak511-a" in (
        _ROOT / "packages" / "api" / "routes" / "enterprise" / "core.py"
    ).read_text(encoding="utf-8")


# --- sak511-b: OpenAPI 503 — fleet-memory status + search ---


SAK511_B_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/enterprise/fleet-memory/status", "get"),
    ("/v1/enterprise/fleet-memory/search", "get"),
)


@pytest.mark.sak511_b
def test_sak511_b_openapi_fleet_memory_503() -> None:
    """sak511-b: fleet-memory status + search document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK511_B_PEEL_OPENAPI:
        assert "application/problem+json" in (
            spec["paths"][path][method]["responses"]["503"]["content"]
        ), path
    assert "sak511-b" in (
        _ROOT / "packages" / "api" / "routes" / "enterprise" / "fleet_memory.py"
    ).read_text(encoding="utf-8")


# --- sak511-c: OpenAPI 503 — fleet-worker health + metrics ---


SAK511_C_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/enterprise/fleet-worker/health", "get"),
    ("/v1/enterprise/fleet-worker/metrics", "get"),
)


@pytest.mark.sak511_c
def test_sak511_c_openapi_fleet_worker_503() -> None:
    """sak511-c: fleet-worker health + metrics document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK511_C_PEEL_OPENAPI:
        assert "application/problem+json" in (
            spec["paths"][path][method]["responses"]["503"]["content"]
        ), path
    assert "sak511-c" in (
        _ROOT / "packages" / "api" / "routes" / "enterprise" / "fleet_ops.py"
    ).read_text(encoding="utf-8")


# --- sak511-d: openapi_peel_503_complete helper ---


@pytest.mark.sak511_d
def test_sak511_d_openapi_peel_503_complete() -> None:
    """sak511-d: openapi_peel_503_complete reports target coverage."""
    peel = (_ROOT / "packages" / "api" / "schemas" / "peel_responses.py").read_text(
        encoding="utf-8",
    )
    assert "sak511-d" in peel
    assert "def openapi_peel_503_complete" in peel
    paths = {
        "/t": {"get": {"responses": {"200": {"description": "ok"}, "503": {}}}},
        "/u": {"post": {"responses": {"200": {"description": "ok"}}}},
    }
    assert openapi_peel_503_complete(paths, [("/t", "get")]) is True
    assert openapi_peel_503_complete(paths, [("/t", "get"), ("/u", "post")]) is False


# --- sak511-e: CI OpenAPI subsets ---


def test_sak511_e_ci_openapi_subsets() -> None:
    """sak511-e: peel-flag-matrix runs sak511 OpenAPI marker subsets."""
    yml = (
        _ROOT.parent / ".github" / "workflows" / "nimbusware-peel.yml"
    ).read_text(encoding="utf-8")
    assert "sak511_a" in yml
    assert "sak511_b" in yml
    assert "sak511_c" in yml
    assert "test_sak511_peel.py" in yml


# --- sak511-f: soak/CI close-out ---


def test_sak511_f_soak_and_ci_closeout() -> None:
    """sak511-f: peel_soak_lib + peel-unit list test_sak511_peel.py."""
    soak = (_ROOT / "scripts" / "peel_soak_lib.py").read_text(encoding="utf-8")
    assert "_assert_sak511_openapi_complete_helper" in soak
    assert "sak511-f — enterprise status/memory/worker OpenAPI + complete helper" in soak
    assert 'label.startswith("sak511")' in soak
    workflow = (
        _ROOT.parent / ".github" / "workflows" / "nimbusware-peel.yml"
    ).read_text(encoding="utf-8")
    peel_unit = workflow.split("  peel-unit:", 1)[1].split("  peel-flag-matrix:", 1)[0]
    assert "tests/unit/test_sak511_peel.py" in peel_unit


# --- sak511-g: OpenAPI 503 — factory-evidence scorecard + export ---


SAK511_G_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/runs/{run_id}/factory-evidence/scorecard.html", "get"),
    ("/v1/runs/{run_id}/factory-evidence/export", "get"),
)


@pytest.mark.sak511_g
def test_sak511_g_openapi_factory_evidence_export_503() -> None:
    """sak511-g: factory-evidence scorecard/export document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK511_G_PEEL_OPENAPI:
        assert "application/problem+json" in (
            spec["paths"][path][method]["responses"]["503"]["content"]
        ), path
    assert "sak511-g" in (
        _ROOT / "packages" / "api" / "routes" / "runs" / "factory_evidence.py"
    ).read_text(encoding="utf-8")


# --- sak511-h: OpenAPI 503 — maker-progress + theater streams ---


SAK511_H_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/runs/{run_id}/maker-progress/stream", "get"),
    ("/v1/runs/{run_id}/theater/stream", "get"),
)


@pytest.mark.sak511_h
def test_sak511_h_openapi_progress_theater_stream_503() -> None:
    """sak511-h: maker-progress/theater streams document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK511_H_PEEL_OPENAPI:
        assert "application/problem+json" in (
            spec["paths"][path][method]["responses"]["503"]["content"]
        ), path
    assert "sak511-h" in (
        _ROOT / "packages" / "api" / "routes" / "runs" / "stream.py"
    ).read_text(encoding="utf-8")
    assert "sak511-h" in (
        _ROOT / "packages" / "api" / "routes" / "runs" / "theater.py"
    ).read_text(encoding="utf-8")


# --- sak511-i: OpenAPI 503 — policy compare/record + audit-export ---


SAK511_I_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/policy/compare/record", "post"),
    ("/v1/runs/{run_id}/audit-export", "get"),
)


@pytest.mark.sak511_i
def test_sak511_i_openapi_policy_record_audit_export_503() -> None:
    """sak511-i: policy compare/record + audit-export document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK511_I_PEEL_OPENAPI:
        assert "application/problem+json" in (
            spec["paths"][path][method]["responses"]["503"]["content"]
        ), path
    assert "sak511-i" in (
        _ROOT / "packages" / "api" / "routes" / "policy.py"
    ).read_text(encoding="utf-8")
    assert "sak511-i" in (
        _ROOT / "packages" / "api" / "routes" / "audit.py"
    ).read_text(encoding="utf-8")


# --- sak511-j: soak/CI deepen ---


def test_sak511_j_soak_and_ci_deepen() -> None:
    """sak511-j: soak/CI cover factory-evidence/stream/policy OpenAPI deepen."""
    soak = (_ROOT / "scripts" / "peel_soak_lib.py").read_text(encoding="utf-8")
    assert "_assert_sak511_exports_streams_openapi" in soak
    assert "sak511-j — factory-evidence/streams/policy OpenAPI" in soak
    yml = (
        _ROOT.parent / ".github" / "workflows" / "nimbusware-peel.yml"
    ).read_text(encoding="utf-8")
    assert "sak511_g" in yml
    assert "sak511_h" in yml
    assert "sak511_i" in yml

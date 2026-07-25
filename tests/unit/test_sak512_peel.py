from __future__ import annotations

import json
from pathlib import Path

import pytest

from api.schemas.peel_responses import list_missing_peel_503_in_openapi_json

_ROOT = Path(__file__).resolve().parents[2]


# --- sak512-a: OpenAPI 503 — bundles catalog promote ---


SAK512_A_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/bundles/catalog-candidates/{run_id}/{candidate_id}/promote", "post"),
    ("/v1/bundles/catalog-candidates/promote-stitch-pending", "post"),
)


@pytest.mark.sak512_a
def test_sak512_a_openapi_bundles_promote_503() -> None:
    """sak512-a: catalog candidate promote routes document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK512_A_PEEL_OPENAPI:
        assert "application/problem+json" in (
            spec["paths"][path][method]["responses"]["503"]["content"]
        ), path
    assert "sak512-a" in (
        _ROOT / "packages" / "api" / "routes" / "bundles.py"
    ).read_text(encoding="utf-8")


# --- sak512-b: OpenAPI 503 — critic-packs PUT + probation-reliability ---


SAK512_B_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/config/critic-packs/{pack_id}", "put"),
    ("/v1/personas/{shelf}/{persona_id}/probation-reliability", "get"),
)


@pytest.mark.sak512_b
def test_sak512_b_openapi_critic_probation_503() -> None:
    """sak512-b: critic-packs PUT + probation-reliability document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK512_B_PEEL_OPENAPI:
        assert "application/problem+json" in (
            spec["paths"][path][method]["responses"]["503"]["content"]
        ), path
    assert "sak512-b" in (
        _ROOT / "packages" / "api" / "routes" / "critic_packs.py"
    ).read_text(encoding="utf-8")
    assert "sak512-b" in (
        _ROOT / "packages" / "api" / "routes" / "personas_handlers.py"
    ).read_text(encoding="utf-8")


# --- sak512-c: OpenAPI 503 — custom-agents CRUD ---


SAK512_C_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/custom-agents", "post"),
    ("/v1/custom-agents/{agent_id}", "get"),
    ("/v1/custom-agents/{agent_id}", "patch"),
    ("/v1/custom-agents/{agent_id}", "delete"),
)


@pytest.mark.sak512_c
def test_sak512_c_openapi_custom_agents_503() -> None:
    """sak512-c: custom-agents CRUD routes document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK512_C_PEEL_OPENAPI:
        assert "application/problem+json" in (
            spec["paths"][path][method]["responses"]["503"]["content"]
        ), path
    assert "sak512-c" in (
        _ROOT / "packages" / "api" / "routes" / "custom_agents.py"
    ).read_text(encoding="utf-8")


# --- sak512-d: list_missing_peel_503_in_openapi_json helper ---


@pytest.mark.sak512_d
def test_sak512_d_list_missing_peel_503_in_openapi_json(tmp_path: Path) -> None:
    """sak512-d: list_missing_peel_503_in_openapi_json reads file targets."""
    peel = (_ROOT / "packages" / "api" / "schemas" / "peel_responses.py").read_text(
        encoding="utf-8",
    )
    assert "sak512-d" in peel
    assert "def list_missing_peel_503_in_openapi_json" in peel
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
    assert list_missing_peel_503_in_openapi_json(path, [("/t", "get")]) == []
    assert list_missing_peel_503_in_openapi_json(
        path,
        [("/t", "get"), ("/u", "post")],
    ) == [("/u", "post")]


# --- sak512-e: CI OpenAPI subsets ---


def test_sak512_e_ci_openapi_subsets() -> None:
    """sak512-e: peel-flag-matrix runs sak512 OpenAPI marker subsets."""
    yml = (
        _ROOT.parent / ".github" / "workflows" / "nimbusware-peel.yml"
    ).read_text(encoding="utf-8")
    assert "sak512_a" in yml
    assert "sak512_b" in yml
    assert "sak512_c" in yml
    assert "test_sak512_peel.py" in yml


# --- sak512-f: soak/CI close-out ---


def test_sak512_f_soak_and_ci_closeout() -> None:
    """sak512-f: peel_soak_lib + peel-unit list test_sak512_peel.py."""
    soak = (_ROOT / "scripts" / "peel_soak_lib.py").read_text(encoding="utf-8")
    assert "_assert_sak512_list_missing_file_helper" in soak
    assert "sak512-f — bundles/critic/custom-agents OpenAPI + file missing helper" in soak
    assert 'label.startswith("sak512")' in soak
    workflow = (
        _ROOT.parent / ".github" / "workflows" / "nimbusware-peel.yml"
    ).read_text(encoding="utf-8")
    peel_unit = workflow.split("  peel-unit:", 1)[1].split("  peel-flag-matrix:", 1)[0]
    assert "tests/unit/test_sak512_peel.py" in peel_unit


# --- sak512-g: OpenAPI 503 — projects POST + GET ---


SAK512_G_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/projects", "post"),
    ("/v1/projects/{project_id}", "get"),
)


@pytest.mark.sak512_g
def test_sak512_g_openapi_projects_create_get_503() -> None:
    """sak512-g: projects POST + GET document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK512_G_PEEL_OPENAPI:
        assert "application/problem+json" in (
            spec["paths"][path][method]["responses"]["503"]["content"]
        ), path
    src = (_ROOT / "packages" / "api" / "routes" / "projects.py").read_text(
        encoding="utf-8",
    )
    assert "sak512-g" in src


# --- sak512-h: OpenAPI 503 — projects PATCH + DELETE ---


SAK512_H_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/projects/{project_id}", "patch"),
    ("/v1/projects/{project_id}", "delete"),
)


@pytest.mark.sak512_h
def test_sak512_h_openapi_projects_mutate_503() -> None:
    """sak512-h: projects PATCH + DELETE document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK512_H_PEEL_OPENAPI:
        assert "application/problem+json" in (
            spec["paths"][path][method]["responses"]["503"]["content"]
        ), path
    src = (_ROOT / "packages" / "api" / "routes" / "projects.py").read_text(
        encoding="utf-8",
    )
    assert "sak512-h" in src


# --- sak512-i: OpenAPI 503 — chat start + scope ---


SAK512_I_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/chat/sessions/{session_id}/start", "post"),
    ("/v1/chat/sessions/{session_id}/scope/publish", "post"),
    ("/v1/chat/sessions/{session_id}/scope/pending", "get"),
    ("/v1/chat/sessions/{session_id}/scope/approve", "post"),
)


@pytest.mark.sak512_i
def test_sak512_i_openapi_chat_start_scope_503() -> None:
    """sak512-i: chat session start + scope routes document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK512_I_PEEL_OPENAPI:
        assert "application/problem+json" in (
            spec["paths"][path][method]["responses"]["503"]["content"]
        ), path
    src = (_ROOT / "packages" / "api" / "routes" / "chat_session.py").read_text(
        encoding="utf-8",
    )
    assert "sak512-i" in src


# --- sak512-j: soak/CI deepen ---


def test_sak512_j_soak_and_ci_deepen() -> None:
    """sak512-j: soak/CI cover projects/chat-start OpenAPI deepen."""
    soak = (_ROOT / "scripts" / "peel_soak_lib.py").read_text(encoding="utf-8")
    assert "_assert_sak512_projects_chat_openapi" in soak
    assert "sak512-j — projects/chat-start/scope OpenAPI" in soak
    yml = (
        _ROOT.parent / ".github" / "workflows" / "nimbusware-peel.yml"
    ).read_text(encoding="utf-8")
    assert "sak512_g" in yml
    assert "sak512_h" in yml
    assert "sak512_i" in yml

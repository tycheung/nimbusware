from __future__ import annotations

import json
from pathlib import Path

import pytest

from api.schemas.peel_responses import count_missing_peel_503_in_openapi_json

_ROOT = Path(__file__).resolve().parents[2]


# --- sak516-a: OpenAPI 503 — commentary + context-artifacts GET ---


SAK516_A_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/chat/sessions/{session_id}/commentary", "post"),
    ("/v1/projects/{project_id}/context-artifacts", "get"),
)


@pytest.mark.sak516_a
def test_sak516_a_openapi_commentary_artifacts_get_503() -> None:
    """sak516-a: commentary + context-artifacts GET document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK516_A_PEEL_OPENAPI:
        assert "application/problem+json" in (
            spec["paths"][path][method]["responses"]["503"]["content"]
        ), path
    assert "sak516-a" in (
        _ROOT / "packages" / "api" / "routes" / "chat_stream.py"
    ).read_text(encoding="utf-8")
    assert "sak516-a" in (
        _ROOT / "packages" / "api" / "routes" / "project_context_artifacts.py"
    ).read_text(encoding="utf-8")


# --- sak516-b: OpenAPI 503 — context-artifacts POST + autopilot presets ---


SAK516_B_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/projects/{project_id}/context-artifacts", "post"),
    ("/v1/autopilot/presets/{level}", "get"),
)


@pytest.mark.sak516_b
def test_sak516_b_openapi_artifacts_post_autopilot_503() -> None:
    """sak516-b: context-artifacts POST + autopilot presets document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK516_B_PEEL_OPENAPI:
        assert "application/problem+json" in (
            spec["paths"][path][method]["responses"]["503"]["content"]
        ), path
    assert "sak516-b" in (
        _ROOT / "packages" / "api" / "routes" / "project_context_artifacts.py"
    ).read_text(encoding="utf-8")
    assert "sak516-b" in (
        _ROOT / "packages" / "api" / "routes" / "platform_user_profiles.py"
    ).read_text(encoding="utf-8")


# --- sak516-c: OpenAPI 503 — enforcement presets + operator-profiles ---


SAK516_C_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/enforcement/presets/{level}", "get"),
    ("/v1/platform/operator-profiles", "put"),
)


@pytest.mark.sak516_c
def test_sak516_c_openapi_enforcement_operator_503() -> None:
    """sak516-c: enforcement presets + operator-profiles PUT document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK516_C_PEEL_OPENAPI:
        assert "application/problem+json" in (
            spec["paths"][path][method]["responses"]["503"]["content"]
        ), path
    assert "sak516-c" in (
        _ROOT / "packages" / "api" / "routes" / "platform_user_profiles.py"
    ).read_text(encoding="utf-8")
    assert "sak516-c" in (
        _ROOT / "packages" / "api" / "routes" / "platform_operator_profiles.py"
    ).read_text(encoding="utf-8")


# --- sak516-d: count_missing_peel_503_in_openapi_json helper ---


@pytest.mark.sak516_d
def test_sak516_d_count_missing_peel_503_in_openapi_json(tmp_path: Path) -> None:
    """sak516-d: count_missing_peel_503_in_openapi_json counts file gaps."""
    peel = (_ROOT / "packages" / "api" / "schemas" / "peel_responses.py").read_text(
        encoding="utf-8",
    )
    assert "sak516-d" in peel
    assert "def count_missing_peel_503_in_openapi_json" in peel
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
    assert count_missing_peel_503_in_openapi_json(path, [("/t", "get")]) == 0
    assert count_missing_peel_503_in_openapi_json(
        path,
        [("/t", "get"), ("/u", "post")],
    ) == 1


# --- sak516-e: CI OpenAPI subsets ---


def test_sak516_e_ci_openapi_subsets() -> None:
    """sak516-e: peel-flag-matrix runs sak516 OpenAPI marker subsets."""
    yml = (
        _ROOT.parent / ".github" / "workflows" / "nimbusware-peel.yml"
    ).read_text(encoding="utf-8")
    assert "sak516_a" in yml
    assert "sak516_b" in yml
    assert "sak516_c" in yml
    assert "test_sak516_peel.py" in yml


# --- sak516-f: soak/CI close-out ---


def test_sak516_f_soak_and_ci_closeout() -> None:
    """sak516-f: peel_soak_lib + peel-unit list test_sak516_peel.py."""
    soak = (_ROOT / "scripts" / "peel_soak_lib.py").read_text(encoding="utf-8")
    assert "_assert_sak516_count_missing_file_helper" in soak
    assert "sak516-f — commentary/artifacts/presets OpenAPI + count-in-file" in soak
    assert 'label.startswith("sak516")' in soak
    workflow = (
        _ROOT.parent / ".github" / "workflows" / "nimbusware-peel.yml"
    ).read_text(encoding="utf-8")
    peel_unit = workflow.split("  peel-unit:", 1)[1].split("  peel-flag-matrix:", 1)[0]
    assert "tests/unit/test_sak516_peel.py" in peel_unit


# --- sak516-g: OpenAPI 503 — autopilot/enforcement user-profile PUTs ---


SAK516_G_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/platform/autopilot/user-profiles/{profile_id}", "put"),
    ("/v1/platform/enforcement/user-profiles/{profile_id}", "put"),
)


@pytest.mark.sak516_g
def test_sak516_g_openapi_user_profile_puts_503() -> None:
    """sak516-g: autopilot/enforcement user-profile PUTs document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK516_G_PEEL_OPENAPI:
        assert "application/problem+json" in (
            spec["paths"][path][method]["responses"]["503"]["content"]
        ), path
    assert "sak516-g" in (
        _ROOT / "packages" / "api" / "routes" / "platform_user_profiles.py"
    ).read_text(encoding="utf-8")


# --- sak516-h: OpenAPI 503 — discipline PUT + participant-context GET ---


SAK516_H_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/users/me/discipline-profile", "put"),
    ("/v1/users/me/participant-context", "get"),
)


@pytest.mark.sak516_h
def test_sak516_h_openapi_discipline_participant_get_503() -> None:
    """sak516-h: discipline PUT + participant-context GET document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK516_H_PEEL_OPENAPI:
        assert "application/problem+json" in (
            spec["paths"][path][method]["responses"]["503"]["content"]
        ), path
    assert "sak516-h" in (
        _ROOT / "packages" / "api" / "routes" / "platform_discipline_profile.py"
    ).read_text(encoding="utf-8")


# --- sak516-i: OpenAPI 503 — participant-context PUT + agent-overlays GET ---


SAK516_I_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/users/me/participant-context", "put"),
    ("/v1/users/me/agent-overlays", "get"),
)


@pytest.mark.sak516_i
def test_sak516_i_openapi_participant_put_overlays_get_503() -> None:
    """sak516-i: participant-context PUT + agent-overlays GET document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK516_I_PEEL_OPENAPI:
        assert "application/problem+json" in (
            spec["paths"][path][method]["responses"]["503"]["content"]
        ), path
    assert "sak516-i" in (
        _ROOT / "packages" / "api" / "routes" / "platform_discipline_profile.py"
    ).read_text(encoding="utf-8")


# --- sak516-j: soak/CI deepen ---


def test_sak516_j_soak_and_ci_deepen() -> None:
    """sak516-j: soak/CI cover user-profile OpenAPI deepen."""
    soak = (_ROOT / "scripts" / "peel_soak_lib.py").read_text(encoding="utf-8")
    assert "_assert_sak516_user_profile_openapi" in soak
    assert "sak516-j — user-profile OpenAPI" in soak
    yml = (
        _ROOT.parent / ".github" / "workflows" / "nimbusware-peel.yml"
    ).read_text(encoding="utf-8")
    assert "sak516_g" in yml
    assert "sak516_h" in yml
    assert "sak516_i" in yml

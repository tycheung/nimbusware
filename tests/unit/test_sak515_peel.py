from __future__ import annotations

import json
from pathlib import Path

import pytest

from api.schemas.peel_responses import peel_503_coverage_in_file

_ROOT = Path(__file__).resolve().parents[2]


# --- sak515-a: OpenAPI 503 — access-grants GET + POST ---


SAK515_A_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/chat/access-grants", "get"),
    ("/v1/chat/access-grants", "post"),
)


@pytest.mark.sak515_a
def test_sak515_a_openapi_access_grants_list_create_503() -> None:
    """sak515-a: access-grants GET + POST document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK515_A_PEEL_OPENAPI:
        assert (
            "application/problem+json"
            in (spec["paths"][path][method]["responses"]["503"]["content"])
        ), path
    assert "sak515-a" in (_ROOT / "packages" / "api" / "routes" / "chat_collab.py").read_text(
        encoding="utf-8"
    )


# --- sak515-b: OpenAPI 503 — access-grants DELETE + effective-role ---


SAK515_B_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/chat/access-grants/{grant_id}", "delete"),
    ("/v1/chat/sessions/{session_id}/effective-role", "get"),
)


@pytest.mark.sak515_b
def test_sak515_b_openapi_grants_delete_effective_role_503() -> None:
    """sak515-b: access-grants DELETE + effective-role document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK515_B_PEEL_OPENAPI:
        assert (
            "application/problem+json"
            in (spec["paths"][path][method]["responses"]["503"]["content"])
        ), path
    assert "sak515-b" in (_ROOT / "packages" / "api" / "routes" / "chat_collab.py").read_text(
        encoding="utf-8"
    )


# --- sak515-c: OpenAPI 503 — participants GET + POST ---


SAK515_C_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/chat/sessions/{session_id}/participants", "get"),
    ("/v1/chat/sessions/{session_id}/participants", "post"),
)


@pytest.mark.sak515_c
def test_sak515_c_openapi_participants_list_add_503() -> None:
    """sak515-c: participants GET + POST document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK515_C_PEEL_OPENAPI:
        assert (
            "application/problem+json"
            in (spec["paths"][path][method]["responses"]["503"]["content"])
        ), path
    assert "sak515-c" in (_ROOT / "packages" / "api" / "routes" / "chat_participants.py").read_text(
        encoding="utf-8"
    )


# --- sak515-d: peel_503_coverage_in_file helper ---


@pytest.mark.sak515_d
def test_sak515_d_peel_503_coverage_in_file(tmp_path: Path) -> None:
    """sak515-d: peel_503_coverage_in_file returns complete + missing from file."""
    peel = (_ROOT / "packages" / "api" / "schemas" / "peel_responses.py").read_text(
        encoding="utf-8",
    )
    assert "sak515-d" in peel
    assert "def peel_503_coverage_in_file" in peel
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
    ok, missing = peel_503_coverage_in_file(path, [("/t", "get")])
    assert ok is True and missing == []
    ok, missing = peel_503_coverage_in_file(path, [("/t", "get"), ("/u", "post")])
    assert ok is False and missing == [("/u", "post")]


# --- sak515-e: CI OpenAPI subsets ---


def test_sak515_e_ci_openapi_subsets() -> None:
    """sak515-e: peel-flag-matrix runs sak515 OpenAPI marker subsets."""
    yml = (_ROOT.parent / ".github" / "workflows" / "nimbusware-peel.yml").read_text(
        encoding="utf-8"
    )
    assert "sak515_a" in yml
    assert "sak515_b" in yml
    assert "sak515_c" in yml
    assert "test_sak515_peel.py" in yml


# --- sak515-f: soak/CI close-out ---


def test_sak515_f_soak_and_ci_closeout() -> None:
    """sak515-f: peel_soak_lib + peel-unit list test_sak515_peel.py."""
    soak = (_ROOT / "scripts" / "peel_soak_lib.py").read_text(encoding="utf-8")
    assert "_assert_sak515_coverage_in_file_helper" in soak
    assert "sak515-f — access-grants/participants OpenAPI + coverage-in-file" in soak
    assert 'label.startswith("sak515")' in soak
    workflow = (_ROOT.parent / ".github" / "workflows" / "nimbusware-peel.yml").read_text(
        encoding="utf-8"
    )
    peel_unit = workflow.split("  peel-unit:", 1)[1].split("  peel-flag-matrix:", 1)[0]
    assert "tests/unit/test_sak515_peel.py" in peel_unit


# --- sak515-g: OpenAPI 503 — participants DELETE + discipline ---


SAK515_G_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/chat/sessions/{session_id}/participants/{user_id}", "delete"),
    ("/v1/chat/sessions/{session_id}/participants/me/discipline", "put"),
)


@pytest.mark.sak515_g
def test_sak515_g_openapi_participants_remove_discipline_503() -> None:
    """sak515-g: participants DELETE + discipline PUT document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK515_G_PEEL_OPENAPI:
        assert (
            "application/problem+json"
            in (spec["paths"][path][method]["responses"]["503"]["content"])
        ), path
    assert "sak515-g" in (_ROOT / "packages" / "api" / "routes" / "chat_participants.py").read_text(
        encoding="utf-8"
    )


# --- sak515-h: OpenAPI 503 — join-preview + invites ---


SAK515_H_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/chat/join-preview", "get"),
    ("/v1/chat/sessions/{session_id}/invites", "post"),
)


@pytest.mark.sak515_h
def test_sak515_h_openapi_join_preview_invites_503() -> None:
    """sak515-h: join-preview + invites document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK515_H_PEEL_OPENAPI:
        assert (
            "application/problem+json"
            in (spec["paths"][path][method]["responses"]["503"]["content"])
        ), path
    assert "sak515-h" in (_ROOT / "packages" / "api" / "routes" / "chat_participants.py").read_text(
        encoding="utf-8"
    )


# --- sak515-i: OpenAPI 503 — join + stream ---


SAK515_I_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/chat/join", "post"),
    ("/v1/chat/sessions/{session_id}/stream", "get"),
)


@pytest.mark.sak515_i
def test_sak515_i_openapi_join_stream_503() -> None:
    """sak515-i: join + session stream document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK515_I_PEEL_OPENAPI:
        assert (
            "application/problem+json"
            in (spec["paths"][path][method]["responses"]["503"]["content"])
        ), path
    assert "sak515-i" in (_ROOT / "packages" / "api" / "routes" / "chat_participants.py").read_text(
        encoding="utf-8"
    )
    assert "sak515-i" in (_ROOT / "packages" / "api" / "routes" / "chat_stream.py").read_text(
        encoding="utf-8"
    )


# --- sak515-j: soak/CI deepen ---


def test_sak515_j_soak_and_ci_deepen() -> None:
    """sak515-j: soak/CI cover join/stream OpenAPI deepen."""
    soak = (_ROOT / "scripts" / "peel_soak_lib.py").read_text(encoding="utf-8")
    assert "_assert_sak515_join_stream_openapi" in soak
    assert "sak515-j — join/stream OpenAPI" in soak
    yml = (_ROOT.parent / ".github" / "workflows" / "nimbusware-peel.yml").read_text(
        encoding="utf-8"
    )
    assert "sak515_g" in yml
    assert "sak515_h" in yml
    assert "sak515_i" in yml

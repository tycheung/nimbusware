from __future__ import annotations

import json
from pathlib import Path

import pytest

from api.schemas.peel_responses import openapi_peel_503_complete_in_file

_ROOT = Path(__file__).resolve().parents[2]


# --- sak513-a: OpenAPI 503 — compute delegate-control + opt-in ---


SAK513_A_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/chat/sessions/{session_id}/compute/delegate-control", "post"),
    ("/v1/chat/sessions/{session_id}/compute/opt-in", "post"),
)


@pytest.mark.sak513_a
def test_sak513_a_openapi_compute_delegate_opt_in_503() -> None:
    """sak513-a: compute delegate-control + opt-in document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK513_A_PEEL_OPENAPI:
        assert (
            "application/problem+json"
            in (spec["paths"][path][method]["responses"]["503"]["content"])
        ), path
    src = (_ROOT / "packages" / "api" / "routes" / "chat_session.py").read_text(
        encoding="utf-8",
    )
    assert "sak513-a" in src


# --- sak513-b: OpenAPI 503 — session optimizer-weights ---


SAK513_B_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/chat/sessions/{session_id}/optimizer-weights", "get"),
    ("/v1/chat/sessions/{session_id}/optimizer-weights", "put"),
)


@pytest.mark.sak513_b
def test_sak513_b_openapi_optimizer_weights_503() -> None:
    """sak513-b: session optimizer-weights GET/PUT document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK513_B_PEEL_OPENAPI:
        assert (
            "application/problem+json"
            in (spec["paths"][path][method]["responses"]["503"]["content"])
        ), path
    src = (_ROOT / "packages" / "api" / "routes" / "chat_session.py").read_text(
        encoding="utf-8",
    )
    assert "sak513-b" in src


# --- sak513-c: OpenAPI 503 — participant-bindings ---


SAK513_C_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/chat/sessions/{session_id}/participant-bindings", "get"),
    ("/v1/chat/sessions/{session_id}/participant-bindings", "put"),
)


@pytest.mark.sak513_c
def test_sak513_c_openapi_participant_bindings_503() -> None:
    """sak513-c: participant-bindings GET/PUT document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK513_C_PEEL_OPENAPI:
        assert (
            "application/problem+json"
            in (spec["paths"][path][method]["responses"]["503"]["content"])
        ), path
    src = (_ROOT / "packages" / "api" / "routes" / "chat_session.py").read_text(
        encoding="utf-8",
    )
    assert "sak513-c" in src


# --- sak513-d: openapi_peel_503_complete_in_file helper ---


@pytest.mark.sak513_d
def test_sak513_d_openapi_peel_503_complete_in_file(tmp_path: Path) -> None:
    """sak513-d: openapi_peel_503_complete_in_file reads file coverage."""
    peel = (_ROOT / "packages" / "api" / "schemas" / "peel_responses.py").read_text(
        encoding="utf-8",
    )
    assert "sak513-d" in peel
    assert "def openapi_peel_503_complete_in_file" in peel
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
    assert openapi_peel_503_complete_in_file(path, [("/t", "get")]) is True
    assert openapi_peel_503_complete_in_file(path, [("/t", "get"), ("/u", "post")]) is False


# --- sak513-e: CI OpenAPI subsets ---


def test_sak513_e_ci_openapi_subsets() -> None:
    """sak513-e: peel-flag-matrix runs sak513 OpenAPI marker subsets."""
    yml = (_ROOT.parent / ".github" / "workflows" / "nimbusware-peel.yml").read_text(
        encoding="utf-8"
    )
    assert "sak513_a" in yml
    assert "sak513_b" in yml
    assert "sak513_c" in yml
    assert "test_sak513_peel.py" in yml


# --- sak513-f: soak/CI close-out ---


def test_sak513_f_soak_and_ci_closeout() -> None:
    """sak513-f: peel_soak_lib + peel-unit list test_sak513_peel.py."""
    soak = (_ROOT / "scripts" / "peel_soak_lib.py").read_text(encoding="utf-8")
    assert "_assert_sak513_complete_in_file_helper" in soak
    assert "sak513-f — chat compute/weights/bindings OpenAPI + complete-in-file" in soak
    assert 'label.startswith("sak513")' in soak
    workflow = (_ROOT.parent / ".github" / "workflows" / "nimbusware-peel.yml").read_text(
        encoding="utf-8"
    )
    peel_unit = workflow.split("  peel-unit:", 1)[1].split("  peel-flag-matrix:", 1)[0]
    assert "tests/unit/test_sak513_peel.py" in peel_unit


# --- sak513-g: OpenAPI 503 — chat sessions POST + GET ---


SAK513_G_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/chat/sessions", "post"),
    ("/v1/chat/sessions", "get"),
)


@pytest.mark.sak513_g
def test_sak513_g_openapi_chat_sessions_list_create_503() -> None:
    """sak513-g: chat sessions POST + GET document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK513_G_PEEL_OPENAPI:
        assert (
            "application/problem+json"
            in (spec["paths"][path][method]["responses"]["503"]["content"])
        ), path
    assert "sak513-g" in (_ROOT / "packages" / "api" / "routes" / "chat.py").read_text(
        encoding="utf-8"
    )


# --- sak513-h: OpenAPI 503 — classify + role-claims ---


SAK513_H_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/chat/classify", "post"),
    ("/v1/chat/sessions/{session_id}/role-claims", "post"),
    ("/v1/chat/sessions/{session_id}/role-claims/{agent_role}", "delete"),
)


@pytest.mark.sak513_h
def test_sak513_h_openapi_classify_role_claims_503() -> None:
    """sak513-h: classify + role-claims document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK513_H_PEEL_OPENAPI:
        assert (
            "application/problem+json"
            in (spec["paths"][path][method]["responses"]["503"]["content"])
        ), path
    assert "sak513-h" in (_ROOT / "packages" / "api" / "routes" / "chat.py").read_text(
        encoding="utf-8"
    )
    assert "sak513-h" in (_ROOT / "packages" / "api" / "routes" / "chat_collab.py").read_text(
        encoding="utf-8"
    )


# --- sak513-i: OpenAPI 503 — host-transfer create/list ---


SAK513_I_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/chat/sessions/{session_id}/host-transfer", "post"),
    ("/v1/chat/sessions/{session_id}/host-transfer", "get"),
)


@pytest.mark.sak513_i
def test_sak513_i_openapi_host_transfer_create_list_503() -> None:
    """sak513-i: host-transfer create/list document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK513_I_PEEL_OPENAPI:
        assert (
            "application/problem+json"
            in (spec["paths"][path][method]["responses"]["503"]["content"])
        ), path
    assert "sak513-i" in (_ROOT / "packages" / "api" / "routes" / "chat_collab.py").read_text(
        encoding="utf-8"
    )


# --- sak513-j: soak/CI deepen ---


def test_sak513_j_soak_and_ci_deepen() -> None:
    """sak513-j: soak/CI cover sessions/classify/host-transfer OpenAPI deepen."""
    soak = (_ROOT / "scripts" / "peel_soak_lib.py").read_text(encoding="utf-8")
    assert "_assert_sak513_sessions_transfer_openapi" in soak
    assert "sak513-j — sessions/classify/host-transfer OpenAPI" in soak
    yml = (_ROOT.parent / ".github" / "workflows" / "nimbusware-peel.yml").read_text(
        encoding="utf-8"
    )
    assert "sak513_g" in yml
    assert "sak513_h" in yml
    assert "sak513_i" in yml

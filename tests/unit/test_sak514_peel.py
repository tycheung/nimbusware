from __future__ import annotations

import json
from pathlib import Path

import pytest

from api.schemas.peel_responses import peel_503_coverage

_ROOT = Path(__file__).resolve().parents[2]


# --- sak514-a: OpenAPI 503 — host-transfer bundle + accept ---


SAK514_A_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/chat/sessions/{session_id}/host-transfer/{transfer_id}/bundle", "get"),
    ("/v1/chat/sessions/{session_id}/host-transfer/{transfer_id}/accept", "post"),
)


@pytest.mark.sak514_a
def test_sak514_a_openapi_host_transfer_bundle_accept_503() -> None:
    """sak514-a: host-transfer bundle + accept document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK514_A_PEEL_OPENAPI:
        assert "application/problem+json" in (
            spec["paths"][path][method]["responses"]["503"]["content"]
        ), path
    assert "sak514-a" in (
        _ROOT / "packages" / "api" / "routes" / "chat_collab.py"
    ).read_text(encoding="utf-8")


# --- sak514-b: OpenAPI 503 — host-transfer import + complete ---


SAK514_B_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/chat/sessions/{session_id}/host-transfer/{transfer_id}/import", "post"),
    ("/v1/chat/sessions/{session_id}/host-transfer/{transfer_id}/complete", "post"),
)


@pytest.mark.sak514_b
def test_sak514_b_openapi_host_transfer_import_complete_503() -> None:
    """sak514-b: host-transfer import + complete document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK514_B_PEEL_OPENAPI:
        assert "application/problem+json" in (
            spec["paths"][path][method]["responses"]["503"]["content"]
        ), path
    assert "sak514-b" in (
        _ROOT / "packages" / "api" / "routes" / "chat_collab.py"
    ).read_text(encoding="utf-8")


# --- sak514-c: OpenAPI 503 — host-transfer decline + library ---


SAK514_C_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/chat/sessions/{session_id}/host-transfer/{transfer_id}/decline", "post"),
    ("/v1/chat/sessions/{session_id}/library", "put"),
)


@pytest.mark.sak514_c
def test_sak514_c_openapi_host_transfer_decline_library_503() -> None:
    """sak514-c: host-transfer decline + library PUT document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK514_C_PEEL_OPENAPI:
        assert "application/problem+json" in (
            spec["paths"][path][method]["responses"]["503"]["content"]
        ), path
    assert "sak514-c" in (
        _ROOT / "packages" / "api" / "routes" / "chat_collab.py"
    ).read_text(encoding="utf-8")


# --- sak514-d: peel_503_coverage helper ---


@pytest.mark.sak514_d
def test_sak514_d_peel_503_coverage() -> None:
    """sak514-d: peel_503_coverage returns complete + missing list."""
    peel = (_ROOT / "packages" / "api" / "schemas" / "peel_responses.py").read_text(
        encoding="utf-8",
    )
    assert "sak514-d" in peel
    assert "def peel_503_coverage" in peel
    paths = {
        "/t": {"get": {"responses": {"200": {"description": "ok"}, "503": {}}}},
        "/u": {"post": {"responses": {"200": {"description": "ok"}}}},
    }
    ok, missing = peel_503_coverage(paths, [("/t", "get")])
    assert ok is True and missing == []
    ok, missing = peel_503_coverage(paths, [("/t", "get"), ("/u", "post")])
    assert ok is False and missing == [("/u", "post")]


# --- sak514-e: CI OpenAPI subsets ---


def test_sak514_e_ci_openapi_subsets() -> None:
    """sak514-e: peel-flag-matrix runs sak514 OpenAPI marker subsets."""
    yml = (
        _ROOT.parent / ".github" / "workflows" / "nimbusware-peel.yml"
    ).read_text(encoding="utf-8")
    assert "sak514_a" in yml
    assert "sak514_b" in yml
    assert "sak514_c" in yml
    assert "test_sak514_peel.py" in yml


# --- sak514-f: soak/CI close-out ---


def test_sak514_f_soak_and_ci_closeout() -> None:
    """sak514-f: peel_soak_lib + peel-unit list test_sak514_peel.py."""
    soak = (_ROOT / "scripts" / "peel_soak_lib.py").read_text(encoding="utf-8")
    assert "_assert_sak514_peel_503_coverage_helper" in soak
    assert "sak514-f — host-transfer deepen OpenAPI + peel_503_coverage" in soak
    assert 'label.startswith("sak514")' in soak
    workflow = (
        _ROOT.parent / ".github" / "workflows" / "nimbusware-peel.yml"
    ).read_text(encoding="utf-8")
    peel_unit = workflow.split("  peel-unit:", 1)[1].split("  peel-flag-matrix:", 1)[0]
    assert "tests/unit/test_sak514_peel.py" in peel_unit


# --- sak514-g: OpenAPI 503 — chat folders GET + POST ---


SAK514_G_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/chat/folders", "get"),
    ("/v1/chat/folders", "post"),
)


@pytest.mark.sak514_g
def test_sak514_g_openapi_folders_list_create_503() -> None:
    """sak514-g: chat folders GET + POST document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK514_G_PEEL_OPENAPI:
        assert "application/problem+json" in (
            spec["paths"][path][method]["responses"]["503"]["content"]
        ), path
    assert "sak514-g" in (
        _ROOT / "packages" / "api" / "routes" / "chat_collab.py"
    ).read_text(encoding="utf-8")


# --- sak514-h: OpenAPI 503 — chat folders PATCH + DELETE ---


SAK514_H_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/chat/folders/{folder_id}", "patch"),
    ("/v1/chat/folders/{folder_id}", "delete"),
)


@pytest.mark.sak514_h
def test_sak514_h_openapi_folders_mutate_503() -> None:
    """sak514-h: chat folders PATCH + DELETE document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK514_H_PEEL_OPENAPI:
        assert "application/problem+json" in (
            spec["paths"][path][method]["responses"]["503"]["content"]
        ), path
    assert "sak514-h" in (
        _ROOT / "packages" / "api" / "routes" / "chat_collab.py"
    ).read_text(encoding="utf-8")


# --- sak514-i: OpenAPI 503 — chat groups ---


SAK514_I_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/chat/groups", "get"),
    ("/v1/chat/groups", "post"),
    ("/v1/chat/groups/{group_id}/members", "post"),
)


@pytest.mark.sak514_i
def test_sak514_i_openapi_groups_503() -> None:
    """sak514-i: chat groups list/create/members document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK514_I_PEEL_OPENAPI:
        assert "application/problem+json" in (
            spec["paths"][path][method]["responses"]["503"]["content"]
        ), path
    assert "sak514-i" in (
        _ROOT / "packages" / "api" / "routes" / "chat_collab.py"
    ).read_text(encoding="utf-8")


# --- sak514-j: soak/CI deepen ---


def test_sak514_j_soak_and_ci_deepen() -> None:
    """sak514-j: soak/CI cover folders/groups OpenAPI deepen."""
    soak = (_ROOT / "scripts" / "peel_soak_lib.py").read_text(encoding="utf-8")
    assert "_assert_sak514_folders_groups_openapi" in soak
    assert "sak514-j — folders/groups OpenAPI" in soak
    yml = (
        _ROOT.parent / ".github" / "workflows" / "nimbusware-peel.yml"
    ).read_text(encoding="utf-8")
    assert "sak514_g" in yml
    assert "sak514_h" in yml
    assert "sak514_i" in yml

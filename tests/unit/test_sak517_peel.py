from __future__ import annotations

import json
from pathlib import Path

import pytest

from api.schemas.peel_responses import ensure_openapi_json_peel_503

_ROOT = Path(__file__).resolve().parents[2]


# --- sak517-a: OpenAPI 503 — agent-overlays PUT + subscription-link ---


SAK517_A_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/users/me/agent-overlays/{discipline}", "put"),
    ("/v1/platform/provider-connections/subscription-link", "post"),
)


@pytest.mark.sak517_a
def test_sak517_a_openapi_overlays_subscription_link_503() -> None:
    """sak517-a: agent-overlays PUT + subscription-link document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK517_A_PEEL_OPENAPI:
        assert (
            "application/problem+json"
            in (spec["paths"][path][method]["responses"]["503"]["content"])
        ), path
    assert "sak517-a" in (
        _ROOT / "packages" / "api" / "routes" / "platform_discipline_profile.py"
    ).read_text(encoding="utf-8")
    assert "sak517-a" in (
        _ROOT / "packages" / "api" / "routes" / "provider_connections.py"
    ).read_text(encoding="utf-8")


# --- sak517-b: OpenAPI 503 — provider-connections PUT + DELETE ---


SAK517_B_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/platform/provider-connections", "put"),
    ("/v1/platform/provider-connections/{connection_id}", "delete"),
)


@pytest.mark.sak517_b
def test_sak517_b_openapi_provider_connections_mutate_503() -> None:
    """sak517-b: provider-connections PUT + DELETE document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK517_B_PEEL_OPENAPI:
        assert (
            "application/problem+json"
            in (spec["paths"][path][method]["responses"]["503"]["content"])
        ), path
    assert "sak517-b" in (
        _ROOT / "packages" / "api" / "routes" / "provider_connections.py"
    ).read_text(encoding="utf-8")


# --- sak517-c: OpenAPI 503 — provider-connections probe ---


SAK517_C_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/platform/provider-connections/{connection_id}/probe", "post"),
)


@pytest.mark.sak517_c
def test_sak517_c_openapi_provider_connections_probe_503() -> None:
    """sak517-c: provider-connections probe document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK517_C_PEEL_OPENAPI:
        assert (
            "application/problem+json"
            in (spec["paths"][path][method]["responses"]["503"]["content"])
        ), path
    assert "sak517-c" in (
        _ROOT / "packages" / "api" / "routes" / "provider_connections.py"
    ).read_text(encoding="utf-8")


# --- sak517-d: ensure_openapi_json_peel_503 helper ---


@pytest.mark.sak517_d
def test_sak517_d_ensure_openapi_json_peel_503(tmp_path: Path) -> None:
    """sak517-d: ensure_openapi_json_peel_503 patches and reports remaining."""
    peel = (_ROOT / "packages" / "api" / "schemas" / "peel_responses.py").read_text(
        encoding="utf-8",
    )
    assert "sak517-d" in peel
    assert "def ensure_openapi_json_peel_503" in peel
    path = tmp_path / "openapi.json"
    path.write_text(
        json.dumps(
            {
                "paths": {
                    "/t": {"get": {"responses": {"200": {"description": "ok"}}}},
                    "/u": {"post": {"responses": {"200": {"description": "ok"}}}},
                },
            },
        ),
        encoding="utf-8",
    )
    added, missing = ensure_openapi_json_peel_503(path, [("/t", "get")])
    assert added == 1 and missing == []
    added, missing = ensure_openapi_json_peel_503(
        path,
        [("/t", "get"), ("/u", "post")],
    )
    assert added == 1 and missing == []
    added, missing = ensure_openapi_json_peel_503(path, [("/t", "get"), ("/u", "post")])
    assert added == 0 and missing == []


# --- sak517-e: CI OpenAPI subsets ---


def test_sak517_e_ci_openapi_subsets() -> None:
    """sak517-e: peel-flag-matrix runs sak517 OpenAPI marker subsets."""
    yml = (_ROOT.parent / ".github" / "workflows" / "nimbusware-peel.yml").read_text(
        encoding="utf-8"
    )
    assert "sak517_a" in yml
    assert "sak517_b" in yml
    assert "sak517_c" in yml
    assert "test_sak517_peel.py" in yml


# --- sak517-f: soak/CI close-out ---


def test_sak517_f_soak_and_ci_closeout() -> None:
    """sak517-f: peel_soak_lib + peel-unit list test_sak517_peel.py."""
    soak = (_ROOT / "scripts" / "peel_soak_lib.py").read_text(encoding="utf-8")
    assert "_assert_sak517_ensure_openapi_helper" in soak
    assert "sak517-f — provider-connections OpenAPI + ensure helper" in soak
    assert 'label.startswith("sak517")' in soak
    workflow = (_ROOT.parent / ".github" / "workflows" / "nimbusware-peel.yml").read_text(
        encoding="utf-8"
    )
    peel_unit = workflow.split("  peel-unit:", 1)[1].split("  peel-flag-matrix:", 1)[0]
    assert "tests/unit/test_sak517_peel.py" in peel_unit


# --- sak517-g: OpenAPI 503 — compute nodes list + register ---


SAK517_G_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/compute/nodes", "get"),
    ("/v1/compute/nodes/register", "post"),
)


@pytest.mark.sak517_g
def test_sak517_g_openapi_compute_nodes_503() -> None:
    """sak517-g: compute nodes list + register document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK517_G_PEEL_OPENAPI:
        assert (
            "application/problem+json"
            in (spec["paths"][path][method]["responses"]["503"]["content"])
        ), path
    assert "sak517-g" in (_ROOT / "packages" / "api" / "routes" / "compute.py").read_text(
        encoding="utf-8"
    )


# --- sak517-h: OpenAPI 503 — heartbeat + claim ---


SAK517_H_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/compute/nodes/{node_id}/heartbeat", "post"),
    ("/v1/compute/work-units/claim", "post"),
)


@pytest.mark.sak517_h
def test_sak517_h_openapi_heartbeat_claim_503() -> None:
    """sak517-h: compute heartbeat + claim document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK517_H_PEEL_OPENAPI:
        assert (
            "application/problem+json"
            in (spec["paths"][path][method]["responses"]["503"]["content"])
        ), path
    assert "sak517-h" in (_ROOT / "packages" / "api" / "routes" / "compute.py").read_text(
        encoding="utf-8"
    )


# --- sak517-i: OpenAPI 503 — queue + complete ---


SAK517_I_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/compute/work-units/queue", "get"),
    ("/v1/compute/work-units/{work_unit_id}/complete", "post"),
)


@pytest.mark.sak517_i
def test_sak517_i_openapi_queue_complete_503() -> None:
    """sak517-i: work-units queue + complete document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK517_I_PEEL_OPENAPI:
        assert (
            "application/problem+json"
            in (spec["paths"][path][method]["responses"]["503"]["content"])
        ), path
    assert "sak517-i" in (_ROOT / "packages" / "api" / "routes" / "compute.py").read_text(
        encoding="utf-8"
    )


# --- sak517-j: soak/CI deepen ---


def test_sak517_j_soak_and_ci_deepen() -> None:
    """sak517-j: soak/CI cover compute nodes OpenAPI deepen."""
    soak = (_ROOT / "scripts" / "peel_soak_lib.py").read_text(encoding="utf-8")
    assert "_assert_sak517_compute_nodes_openapi" in soak
    assert "sak517-j — compute nodes OpenAPI" in soak
    yml = (_ROOT.parent / ".github" / "workflows" / "nimbusware-peel.yml").read_text(
        encoding="utf-8"
    )
    assert "sak517_g" in yml
    assert "sak517_h" in yml
    assert "sak517_i" in yml

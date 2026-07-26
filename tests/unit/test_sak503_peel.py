from __future__ import annotations

import json
from pathlib import Path

import pytest

from api.schemas.openapi import PROBLEM_RESPONSE_503
from api.schemas.peel_responses import (
    enterprise_peel_json_openapi_responses,
    with_enterprise_peel_503,
)

_ROOT = Path(__file__).resolve().parents[2]


# --- sak503-a: OpenAPI 503 — policy compare + critic-packs ---


SAK503_A_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/policy/compare", "get"),
    ("/v1/config/critic-packs", "get"),
)


@pytest.mark.sak503_a
def test_sak503_a_openapi_policy_critic_packs_503() -> None:
    """sak503-a: policy/compare + critic-packs document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK503_A_PEEL_OPENAPI:
        assert (
            "application/problem+json"
            in (spec["paths"][path][method]["responses"]["503"]["content"])
        ), path
    assert "sak503-a" in (_ROOT / "packages" / "api" / "routes" / "policy.py").read_text(
        encoding="utf-8"
    )
    assert "sak503-a" in (_ROOT / "packages" / "api" / "routes" / "critic_packs.py").read_text(
        encoding="utf-8"
    )


# --- sak503-b: OpenAPI 503 — deploy environments + discipline profile ---


SAK503_B_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/platform/deploy/environments", "get"),
    ("/v1/users/me/discipline-profile", "get"),
)


@pytest.mark.sak503_b
def test_sak503_b_openapi_deploy_discipline_503() -> None:
    """sak503-b: deploy environments + discipline-profile document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK503_B_PEEL_OPENAPI:
        assert (
            "application/problem+json"
            in (spec["paths"][path][method]["responses"]["503"]["content"])
        ), path
    assert "sak503-b" in (_ROOT / "packages" / "api" / "routes" / "platform_deploy.py").read_text(
        encoding="utf-8"
    )
    assert "sak503-b" in (
        _ROOT / "packages" / "api" / "routes" / "platform_discipline_profile.py"
    ).read_text(encoding="utf-8")


# --- sak503-c: OpenAPI 503 — fleet enforcement/standards ---


SAK503_C_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/enterprise/tenants/{tenant_ref}/enforcement-policy", "get"),
    ("/v1/enterprise/tenants/{tenant_ref}/standards-policy", "get"),
)


@pytest.mark.sak503_c
def test_sak503_c_openapi_fleet_enforcement_standards_503() -> None:
    """sak503-c: enforcement/standards policy GETs document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK503_C_PEEL_OPENAPI:
        assert (
            "application/problem+json"
            in (spec["paths"][path][method]["responses"]["503"]["content"])
        ), path
    assert "sak503-c" in (
        _ROOT / "packages" / "api" / "routes" / "enterprise" / "fleet_enforcement.py"
    ).read_text(encoding="utf-8")
    assert "sak503-c" in (
        _ROOT / "packages" / "api" / "routes" / "enterprise" / "fleet_standards.py"
    ).read_text(encoding="utf-8")


# --- sak503-d: with_enterprise_peel_503 helper ---


@pytest.mark.sak503_d
def test_sak503_d_with_enterprise_peel_503_merges() -> None:
    """sak503-d: with_enterprise_peel_503 merges 503 into existing responses."""
    peel = (_ROOT / "packages" / "api" / "schemas" / "peel_responses.py").read_text(
        encoding="utf-8",
    )
    assert "sak503-d" in peel
    assert "def with_enterprise_peel_503" in peel
    merged = with_enterprise_peel_503({200: {"description": "ok"}})
    assert merged[200]["description"] == "ok"
    assert merged[503] is PROBLEM_RESPONSE_503
    assert enterprise_peel_json_openapi_responses()[503] is PROBLEM_RESPONSE_503
    assert "with_enterprise_peel_503()" in (
        _ROOT / "packages" / "api" / "routes" / "enterprise" / "fleet_enforcement.py"
    ).read_text(encoding="utf-8")


# --- sak503-e: CI OpenAPI subsets ---


def test_sak503_e_ci_openapi_subsets() -> None:
    """sak503-e: peel-flag-matrix runs sak503 OpenAPI marker subsets."""
    yml = (_ROOT.parent / ".github" / "workflows" / "nimbusware-peel.yml").read_text(
        encoding="utf-8"
    )
    assert "sak503_a" in yml
    assert "sak503_b" in yml
    assert "sak503_c" in yml
    assert "test_sak503_peel.py" in yml


# --- sak503-f: soak/CI close-out ---


def test_sak503_f_soak_and_ci_closeout() -> None:
    """sak503-f: peel_soak_lib + peel-unit list test_sak503_peel.py."""
    soak = (_ROOT / "scripts" / "peel_soak_lib.py").read_text(encoding="utf-8")
    assert "_assert_sak503_enterprise_peel_helper" in soak
    assert "sak503-f — policy/deploy/fleet OpenAPI" in soak
    assert 'label.startswith("sak503")' in soak
    workflow = (_ROOT.parent / ".github" / "workflows" / "nimbusware-peel.yml").read_text(
        encoding="utf-8"
    )
    peel_unit = workflow.split("  peel-unit:", 1)[1].split("  peel-flag-matrix:", 1)[0]
    assert "tests/unit/test_sak503_peel.py" in peel_unit


# --- sak503-g: OpenAPI 503 — compact + compactions revert ---


SAK503_G_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/runs/{run_id}/compact", "post"),
    ("/v1/runs/{run_id}/compactions/{compaction_id}/revert", "post"),
)


@pytest.mark.sak503_g
def test_sak503_g_openapi_compact_compactions_503() -> None:
    """sak503-g: compact + compaction revert document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK503_G_PEEL_OPENAPI:
        assert (
            "application/problem+json"
            in (spec["paths"][path][method]["responses"]["503"]["content"])
        ), path
    assert "sak503-g" in (_ROOT / "packages" / "api" / "routes" / "runs" / "compact.py").read_text(
        encoding="utf-8"
    )
    assert "sak503-g" in (
        _ROOT / "packages" / "api" / "routes" / "runs" / "compactions.py"
    ).read_text(encoding="utf-8")


# --- sak503-h: OpenAPI 503 — context_budget + replay-from ---


SAK503_H_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/runs/{run_id}/context_budget", "get"),
    ("/v1/runs/{run_id}/replay-from", "post"),
)


@pytest.mark.sak503_h
def test_sak503_h_openapi_budget_replay_503() -> None:
    """sak503-h: context_budget + replay-from document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK503_H_PEEL_OPENAPI:
        assert (
            "application/problem+json"
            in (spec["paths"][path][method]["responses"]["503"]["content"])
        ), path
    assert "sak503-h" in (
        _ROOT / "packages" / "api" / "routes" / "runs" / "context_budget.py"
    ).read_text(encoding="utf-8")
    assert "sak503-h" in (
        _ROOT / "packages" / "api" / "routes" / "runs" / "replay_from.py"
    ).read_text(encoding="utf-8")


# --- sak503-i: OpenAPI 503 — integrations external-chat ---


SAK503_I_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/integrations/external-chat", "get"),
    ("/v1/integrations/external-chat/webhook", "post"),
)


@pytest.mark.sak503_i
def test_sak503_i_openapi_integrations_503() -> None:
    """sak503-i: external-chat capabilities + webhook document 503."""
    spec = json.loads(
        (_ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json").read_text(
            encoding="utf-8",
        ),
    )
    for path, method in SAK503_I_PEEL_OPENAPI:
        assert (
            "application/problem+json"
            in (spec["paths"][path][method]["responses"]["503"]["content"])
        ), path
    assert "sak503-i" in (_ROOT / "packages" / "api" / "routes" / "integrations.py").read_text(
        encoding="utf-8"
    )


# --- sak503-j: soak/CI deepen ---


def test_sak503_j_soak_and_ci_deepen() -> None:
    """sak503-j: soak run compact OpenAPI asserts + CI sak503_g/h/i markers."""
    soak = (_ROOT / "scripts" / "peel_soak_lib.py").read_text(encoding="utf-8")
    assert "_assert_sak503_run_compact_openapi" in soak
    assert "sak503-j — run compact/budget/integrations OpenAPI" in soak
    yml = (_ROOT.parent / ".github" / "workflows" / "nimbusware-peel.yml").read_text(
        encoding="utf-8"
    )
    assert "sak503_g" in yml
    assert "sak503_h" in yml
    assert "sak503_i" in yml

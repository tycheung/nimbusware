from __future__ import annotations

import json
from pathlib import Path

import pytest

from api.schemas.peel_responses import (
    PEEL_503_OAUTH_SKIP,
    iter_openapi_json_operations,
    list_missing_product_peel_503_in_openapi_json,
    openapi_json_peel_503_report,
    openapi_product_peel_503_complete_in_file,
)

_ROOT = Path(__file__).resolve().parents[2]
_OPENAPI = _ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json"


# --- sak521-a: iter_openapi_json_operations ---


@pytest.mark.sak521_a
def test_sak521_a_iter_openapi_json_operations() -> None:
    """sak521-a: iter_openapi_json_operations lists path/method pairs."""
    peel = (_ROOT / "packages" / "api" / "schemas" / "peel_responses.py").read_text(
        encoding="utf-8",
    )
    assert "sak521-a" in peel
    assert "iter_openapi_json_operations" in peel
    ops = iter_openapi_json_operations(_OPENAPI)
    assert ("/v1/maker/push-subscriptions", "post") in ops
    assert ("/v1/admin/ui/enterprise/fleet-enforcement-policy", "get") in ops
    assert len(ops) > 100


# --- sak521-b: PEEL_503_OAUTH_SKIP allowlist ---


@pytest.mark.sak521_b
def test_sak521_b_oauth_skip_allowlist() -> None:
    """sak521-b: oauth mock/login paths are skip-listed for product peel."""
    peel = (_ROOT / "packages" / "api" / "schemas" / "peel_responses.py").read_text(
        encoding="utf-8",
    )
    assert "sak521-b" in peel
    assert "PEEL_503_OAUTH_SKIP" in peel
    assert ("/v1/admin/oauth/login", "get") in PEEL_503_OAUTH_SKIP
    assert (
        "/v1/platform/provider-subscriptions/oauth/mock-authorize",
        "get",
    ) in PEEL_503_OAUTH_SKIP
    missing = list_missing_product_peel_503_in_openapi_json(_OPENAPI)
    for skipped in PEEL_503_OAUTH_SKIP:
        assert skipped not in missing


# --- sak521-c: product peel 503 complete gate ---


@pytest.mark.sak521_c
def test_sak521_c_product_peel_503_complete() -> None:
    """sak521-c: non-oauth OpenAPI ops all document peel 503."""
    peel = (_ROOT / "packages" / "api" / "schemas" / "peel_responses.py").read_text(
        encoding="utf-8",
    )
    assert "sak521-c" in peel
    assert "openapi_product_peel_503_complete_in_file" in peel
    assert openapi_product_peel_503_complete_in_file(_OPENAPI) is True
    assert list_missing_product_peel_503_in_openapi_json(_OPENAPI) == []


# --- sak521-d: openapi_json_peel_503_report DRY via coverage_in_file ---


@pytest.mark.sak521_d
def test_sak521_d_report_uses_coverage_in_file(tmp_path: Path) -> None:
    """sak521-d: openapi_json_peel_503_report DRYs via peel_503_coverage_in_file."""
    peel = (_ROOT / "packages" / "api" / "schemas" / "peel_responses.py").read_text(
        encoding="utf-8",
    )
    assert "sak521-d" in peel
    assert "peel_503_coverage_in_file" in peel
    path = tmp_path / "openapi.json"
    path.write_text(
        json.dumps(
            {
                "paths": {
                    "/t": {
                        "get": {
                            "responses": {"200": {"description": "ok"}, "503": {}},
                        },
                    },
                    "/u": {"post": {"responses": {"200": {"description": "ok"}}}},
                },
            },
        ),
        encoding="utf-8",
    )
    report = openapi_json_peel_503_report(path, [("/t", "get"), ("/u", "post")])
    assert report["complete"] is False
    assert report["count"] == 1
    assert report["missing"] == [("/u", "post")]


# --- sak521-e: CI OpenAPI subsets ---


def test_sak521_e_ci_openapi_subsets() -> None:
    """sak521-e: peel-flag-matrix runs sak521 OpenAPI marker subsets."""
    yml = (_ROOT.parent / ".github" / "workflows" / "nimbusware-peel.yml").read_text(
        encoding="utf-8"
    )
    assert "sak521_a" in yml
    assert "sak521_b" in yml
    assert "sak521_c" in yml
    assert "test_sak521_peel.py" in yml


# --- sak521-f: soak/CI close-out ---


def test_sak521_f_soak_and_ci_closeout() -> None:
    """sak521-f: peel_soak_lib + peel-unit list test_sak521_peel.py."""
    soak = (_ROOT / "scripts" / "peel_soak_lib.py").read_text(encoding="utf-8")
    assert "_assert_sak521_product_complete_helper" in soak
    assert "sak521-f — product peel complete + oauth skip" in soak
    assert 'label.startswith("sak521")' in soak
    workflow = (_ROOT.parent / ".github" / "workflows" / "nimbusware-peel.yml").read_text(
        encoding="utf-8"
    )
    peel_unit = workflow.split("  peel-unit:", 1)[1].split("  peel-flag-matrix:", 1)[0]
    assert "tests/unit/test_sak521_peel.py" in peel_unit

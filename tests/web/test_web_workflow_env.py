from __future__ import annotations

from pathlib import Path

import yaml

_REPO = Path(__file__).resolve().parents[2]
_WEB_WORKFLOW = _REPO / ".github" / "workflows" / "web-tests.yml"
_PLAYWRIGHT_CONFIG = _REPO / "tests" / "e2e" / "web" / "playwright.config.ts"
_CI_WORKFLOW = _REPO / ".github" / "workflows" / "ci.yml"


def test_web_tests_workflow_does_not_start_postgres() -> None:
    text = _WEB_WORKFLOW.read_text(encoding="utf-8")
    assert "postgres:" not in text.lower()
    assert "NIMBUSWARE_SKIP_PREFLIGHT" in text


def test_playwright_config_clears_database_url() -> None:
    text = _PLAYWRIGHT_CONFIG.read_text(encoding="utf-8")
    assert "NIMBUSWARE_DATABASE_URL" in text
    assert 'NIMBUSWARE_DATABASE_URL: ""' in text


def test_ci_e2e_job_uses_postgres_not_web_tests() -> None:
    ci = _CI_WORKFLOW.read_text(encoding="utf-8")
    web = _WEB_WORKFLOW.read_text(encoding="utf-8")
    assert "postgres:" in ci.lower()
    assert "postgres:" not in web.lower()
    assert "tests/e2e/web" in web


def test_web_parity_matrix_documents_variant_arena() -> None:
    matrix = yaml.safe_load(
        (_REPO / "tests" / "web" / "parity_matrix.yaml").read_text(encoding="utf-8"),
    )
    maker = matrix.get("maker") or []
    assert any(row.get("id") == "variant_arena_detail" for row in maker)

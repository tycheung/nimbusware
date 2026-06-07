from __future__ import annotations

from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_CI = _REPO / ".github" / "workflows" / "ci.yml"


def test_ci_e2e_job_has_flake_rerun_budget() -> None:
    text = _CI.read_text(encoding="utf-8")
    assert "  e2e:" in text
    assert "--reruns 1" in text
    assert "NIMBUSWARE_E2E_FLAKE_RETRIES" in text


def test_e2e_conftest_reads_flake_retry_env() -> None:
    path = _REPO / "tests" / "e2e" / "conftest.py"
    body = path.read_text(encoding="utf-8")
    assert "NIMBUSWARE_E2E_FLAKE_RETRIES" in body

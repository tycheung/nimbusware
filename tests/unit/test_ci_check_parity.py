from __future__ import annotations

from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_CI = _REPO / ".github" / "workflows" / "ci.yml"
_PS1 = _REPO / "scripts" / "ci" / "ci_check.ps1"
_SH = _REPO / "scripts" / "ci" / "ci_check.sh"

_STREAM_CI_YML = ("run_stream.py", "aggregate_stream_results.py")
_STREAM_LOCAL = ("run_all_streams.py", "nimbusware-monorepo")

_CRITICAL_STEPS = (
    "rebuild_bundle_faiss_if_stale.py --dry-run",
    "ruff check packages tests",
    "audit_operator_env.py",
    "run_openapi_ts_ci_gate.py",
    "ruff format --check packages tests",
    "mypy_ci_targets.py",
    "bandit",
    "pip-audit",
    "pytest tests",
    "coverage_package_floors.py",
    "test_slice_e2e_workflow.py",
    "run_framework_pack_ci_gate.py",
    "run_bootstrap_ci_gate.py",
    "run_publish_bootstrap_ci_gate.py",
    "run_publish_launcher_ci_gate.py",
    "run_playwright_button_ci_gate.py",
    "run_publish_vscode_ci_gate.py",
    "run_intent_to_patch_ci_gate.py",
    "run_classifier_acceptance_ci_gate.py",
)


def test_ci_yml_stream_jobs_includes_streams() -> None:
    text = _CI.read_text(encoding="utf-8")
    assert "  streams:" in text
    assert "  stream-aggregate:" in text
    for step in _STREAM_CI_YML:
        assert step in text, f"missing in ci.yml streams jobs: {step}"
    assert "hygiene" in text and "performance" in text


def test_ci_yml_unit_job_includes_critical_steps() -> None:
    text = _CI.read_text(encoding="utf-8")
    unit_block = text[text.index("  unit:") : text.index("  web:")]
    for step in _CRITICAL_STEPS:
        assert step in unit_block, f"missing in ci.yml unit job: {step}"


def test_ci_check_ps1_includes_critical_steps() -> None:
    text = _PS1.read_text(encoding="utf-8")
    for step in (*_STREAM_LOCAL, *_CRITICAL_STEPS):
        assert step in text, f"missing in ci_check.ps1: {step}"


def test_ci_check_sh_includes_critical_steps() -> None:
    text = _SH.read_text(encoding="utf-8")
    for step in (*_STREAM_LOCAL, *_CRITICAL_STEPS):
        assert step in text, f"missing in ci_check.sh: {step}"


def test_ci_yml_has_web_job_with_vitest_and_playwright() -> None:
    text = _CI.read_text(encoding="utf-8")
    web_start = text.index("  web:")
    web_block = text[web_start : text.index("  integration:")]
    assert "maker_web" in web_block
    assert "admin_ui" in web_block
    assert "playwright install chromium" in web_block


def test_ci_check_scripts_compile_vscode_extension() -> None:
    ps1 = _PS1.read_text(encoding="utf-8")
    sh = _SH.read_text(encoding="utf-8")
    for text in (ps1, sh):
        assert "extensions/nimbusware-status" in text or "extensions\\nimbusware-status" in text
        assert "npm run compile" in text


def test_ci_check_scripts_document_optional_integration_flags() -> None:
    ps1 = _PS1.read_text(encoding="utf-8")
    sh = _SH.read_text(encoding="utf-8")
    assert "WithIntegration" in ps1
    assert "WithE2e" in ps1
    assert "with-integration" in sh
    assert "with-e2e" in sh
    assert "run_integration_like_ci" in ps1
    assert "run_integration_like_ci" in sh

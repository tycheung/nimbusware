from __future__ import annotations

from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_WORKFLOW = _REPO / ".github" / "workflows" / "publish_bootstrap.yml"

_REQUIRED_TOKENS = (
    "workflow_dispatch",
    "publish_testpypi",
    "publish_pypi",
    "TESTPYPI_API_TOKEN",
    "PYPI_API_TOKEN",
    "Require TestPyPI token",
    "Require PyPI token",
    "nimbusware-bootstrap",
    "twine upload",
    "nimbusware-bootstrap --print-only",
)


def test_publish_bootstrap_workflow_has_required_steps() -> None:
    text = _WORKFLOW.read_text(encoding="utf-8")
    for token in _REQUIRED_TOKENS:
        assert token in text, f"missing in publish_bootstrap.yml: {token}"


def test_publish_bootstrap_workflow_prod_token_guard_before_upload() -> None:
    text = _WORKFLOW.read_text(encoding="utf-8")
    guard = text.index("Require PyPI token")
    upload = text.index("Publish to PyPI")
    assert guard < upload


def test_publish_bootstrap_workflow_default_inputs_do_not_publish() -> None:
    text = _WORKFLOW.read_text(encoding="utf-8")
    assert "default: false" in text
    assert text.count("if: inputs.publish_pypi == true") >= 2
    assert text.count("if: inputs.publish_testpypi == true") >= 2

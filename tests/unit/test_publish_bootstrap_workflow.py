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
    "nimbusware-bootstrap",
    "twine upload",
    "nimbusware-bootstrap --print-only",
)


def test_publish_bootstrap_workflow_has_required_steps() -> None:
    text = _WORKFLOW.read_text(encoding="utf-8")
    for token in _REQUIRED_TOKENS:
        assert token in text, f"missing in publish_bootstrap.yml: {token}"

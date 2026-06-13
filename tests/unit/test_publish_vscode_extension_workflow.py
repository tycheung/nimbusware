from __future__ import annotations

from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_WORKFLOW = _REPO / ".github" / "workflows" / "publish_vscode_extension.yml"

_REQUIRED_TOKENS = (
    "workflow_dispatch",
    "publish_marketplace",
    "VSCE_PAT",
    "Require VSCE token",
    "nimbusware-status",
    "vsce package",
    "vsce publish",
)


def test_publish_vscode_extension_workflow_has_required_steps() -> None:
    text = _WORKFLOW.read_text(encoding="utf-8")
    for token in _REQUIRED_TOKENS:
        assert token in text, f"missing in publish_vscode_extension.yml: {token}"


def test_publish_vscode_extension_workflow_token_guard_before_publish() -> None:
    text = _WORKFLOW.read_text(encoding="utf-8")
    guard = text.index("- name: Require VSCE token")
    publish = text.index("- name: Publish to Visual Studio Marketplace")
    assert guard < publish


def test_publish_vscode_extension_workflow_default_input_does_not_publish() -> None:
    text = _WORKFLOW.read_text(encoding="utf-8")
    assert "default: false" in text
    assert text.count("if: inputs.publish_marketplace == true") >= 2

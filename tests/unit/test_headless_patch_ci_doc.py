from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def test_headless_patch_ci_doc_and_sample_workflow_exist() -> None:
    doc = REPO / "docs" / "deploy" / "headless-patch-ci.md"
    workflow = REPO / ".github" / "workflows" / "nimbusware_patch_sample.yml"
    assert doc.is_file()
    assert workflow.is_file()
    text = doc.read_text(encoding="utf-8")
    assert "work_type_source=ci" in text
    assert "workflow_profile=patch" in text
    wf = workflow.read_text(encoding="utf-8")
    assert "lifecycle/start" in wf
    assert "lifecycle/slice" in wf

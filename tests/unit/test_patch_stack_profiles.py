from __future__ import annotations

from pathlib import Path

from orchestrator.workflow.profiles import workflow_profile_path

REPO = Path(__file__).resolve().parents[2]


def test_patch_go_profile_exists_and_allows_go_globs() -> None:
    path = workflow_profile_path(REPO, "patch_go")
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert "**/*.go" in text
    assert "slice.gate" in text


def test_patch_stack_fixtures_exist() -> None:
    fixtures = Path(__file__).resolve().parents[1] / "fixtures" / "repos"
    assert (fixtures / "tiny_go_app" / "go.mod").is_file()
    assert (fixtures / "tiny_go_app" / "calculator_test.go").is_file()
    assert (fixtures / "tiny_jvm_app" / "pom.xml").is_file()
    assert (
        fixtures / "tiny_jvm_app" / "src" / "main" / "java" / "com" / "example" / "Calculator.java"
    ).is_file()


def test_patch_jvm_profile_exists_and_allows_jvm_globs() -> None:
    path = workflow_profile_path(REPO, "patch_jvm")
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert ".java" in text or "java" in text
    assert "slice.gate" in text

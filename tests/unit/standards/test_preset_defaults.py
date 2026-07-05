from __future__ import annotations

from standards.preset_defaults import (
    default_bundle_ids_for_preset,
    facade_language,
    infer_facade_from_workspace,
    preset_defaults_summary,
)


def test_python_fastapi_level5_includes_hygiene_and_error_handling() -> None:
    bundles = default_bundle_ids_for_preset("python-fastapi", 5)
    assert "python-agent-hygiene" in bundles
    assert "error-handling" in bundles
    assert "nasa-rule-of-ten" not in bundles


def test_python_fastapi_level9_includes_nasa_for_memory_unsafe() -> None:
    bundles = default_bundle_ids_for_preset("python-fastapi", 9)
    assert "nasa-rule-of-ten" in bundles
    assert "oop-solid" in bundles


def test_typescript_level9_skips_nasa() -> None:
    bundles = default_bundle_ids_for_preset("typescript-react", 9)
    assert "fp-immutability" in bundles
    assert "nasa-rule-of-ten" not in bundles
    assert "typescript-agent-hygiene" in bundles


def test_go_level3_includes_go_hygiene_only() -> None:
    bundles = default_bundle_ids_for_preset("go-service", 3)
    assert bundles == ("go-agent-hygiene",)


def test_level0_has_no_bundles() -> None:
    assert default_bundle_ids_for_preset("python-fastapi", 0) == ()


def test_facade_language_from_manifest() -> None:
    assert facade_language("typescript-react") == "typescript"
    assert facade_language("go-service") == "go"


def test_infer_facade_from_pyproject(tmp_path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    assert infer_facade_from_workspace(tmp_path) == "python-fastapi"


def test_preset_defaults_summary_shape() -> None:
    summary = preset_defaults_summary("python-fastapi", 7)
    assert summary["language"] == "python"
    assert summary["memory_safe"] is False
    assert "oop-solid" in summary["bundle_ids"]

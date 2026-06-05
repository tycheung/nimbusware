from __future__ import annotations

from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_PYPROJECT = _REPO / "pyproject.toml"

_STRICT_MODULES = frozenset(
    {
        "nimbusware_api.*",
        "nimbusware_api.schemas.ollama",
        "nimbusware_api.routes.ollama",
        "nimbusware_api.errors",
    },
)

_PIPELINE_BLANKET_IGNORE = 'module = ["nimbusware_orchestrator._pipeline.*"]'


def test_api_listed_in_mypy_strict_override() -> None:
    text = _PYPROJECT.read_text(encoding="utf-8")
    assert "ignore_errors = false" in text
    for module in _STRICT_MODULES:
        assert module in text, f"missing strict mypy override entry for {module}"


def test_pipeline_blanket_ignore_removed() -> None:
    text = _PYPROJECT.read_text(encoding="utf-8")
    assert _PIPELINE_BLANKET_IGNORE not in text

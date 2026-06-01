from __future__ import annotations

from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_PYPROJECT = _REPO / "pyproject.toml"

_STRICT_MODULES = frozenset(
    {
        "nimbusware_api.schemas.ollama",
        "nimbusware_api.routes.ollama",
        "nimbusware_api.errors",
        "hermes_orchestrator.ollama_manage",
        "hermes_orchestrator.ollama_user_policy",
        "nimbusware_console.services.ollama",
        "nimbusware_maker.services.ollama",
    },
)


def test_ollama_modules_listed_in_mypy_strict_override() -> None:
    text = _PYPROJECT.read_text(encoding="utf-8")
    assert "ignore_errors = false" in text
    for module in _STRICT_MODULES:
        assert module in text, f"missing strict mypy override entry for {module}"

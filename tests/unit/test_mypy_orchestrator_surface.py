from __future__ import annotations

from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_PYPROJECT = _REPO / "pyproject.toml"
_TARGETS = _REPO / "scripts" / "mypy_ci_targets.py"

_ORCHESTRATOR_STRICT = frozenset(
    {
        "hermes_orchestrator.ollama_manage",
        "hermes_orchestrator.ollama_user_policy",
        "hermes_orchestrator.preflight",
        "hermes_orchestrator.merge",
        "hermes_orchestrator.workflow_profiles",
    },
)

_PIPELINE_IGNORED = "hermes_orchestrator._pipeline.*"


def test_orchestrator_strict_islands_listed() -> None:
    text = _PYPROJECT.read_text(encoding="utf-8")
    for module in _ORCHESTRATOR_STRICT:
        assert module in text, f"missing strict mypy override entry for {module}"


def test_pipeline_mixins_still_ignored() -> None:
    text = _PYPROJECT.read_text(encoding="utf-8")
    assert _PIPELINE_IGNORED in text


def test_tranche_e_paths_in_ci_targets() -> None:
    text = _TARGETS.read_text(encoding="utf-8")
    assert "packages/hermes_orchestrator/merge.py" in text
    assert "packages/hermes_orchestrator/workflow_profiles.py" in text

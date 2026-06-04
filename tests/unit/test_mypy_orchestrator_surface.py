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
        "hermes_orchestrator._pipeline.base",
        "hermes_orchestrator._pipeline._helpers",
        "hermes_orchestrator._pipeline.create_run",
        "hermes_orchestrator._pipeline.micro_slice",
        "hermes_orchestrator._pipeline.lifecycle_verify",
        "hermes_orchestrator._pipeline.writers",
        "hermes_orchestrator._pipeline.lifecycle_plan",
        "hermes_orchestrator._pipeline.optional_critique",
        "hermes_orchestrator._pipeline.escalation",
        "hermes_orchestrator._pipeline.critique_gates_helpers",
        "hermes_orchestrator._pipeline.critique_gates_optional_emit",
        "hermes_orchestrator._pipeline.critique_gates_stage_failed",
        "hermes_orchestrator._pipeline.critique_gates",
        "hermes_orchestrator._pipeline.lifecycle",
        "hermes_orchestrator._pipeline.lifecycle_start",
        "hermes_orchestrator._pipeline.optional_stages_research",
        "hermes_orchestrator._pipeline.optional_stages_stitch",
        "hermes_orchestrator._pipeline.optional_stages_integrator",
        "hermes_orchestrator._pipeline.optional_stages_integration",
        "hermes_orchestrator._pipeline.optional_stages_self_refinement",
        "hermes_orchestrator._pipeline.optional_stages_agent_evaluator",
        "hermes_orchestrator._pipeline.optional_stages",
        "hermes_orchestrator._pipeline.compose",
        "hermes_orchestrator._pipeline.protocol_hosts",
        "hermes_orchestrator._pipeline.pipeline_scraper",
        "hermes_orchestrator._pipeline.dev_factory",
        "hermes_orchestrator._pipeline.__init__",
    },
)

_PIPELINE_BLANKET_IGNORE = 'module = ["hermes_orchestrator._pipeline.*"]'


def test_orchestrator_strict_islands_listed() -> None:
    text = _PYPROJECT.read_text(encoding="utf-8")
    for module in _ORCHESTRATOR_STRICT:
        assert module in text, f"missing strict mypy override entry for {module}"


def test_pipeline_blanket_ignore_removed() -> None:
    text = _PYPROJECT.read_text(encoding="utf-8")
    assert _PIPELINE_BLANKET_IGNORE not in text


def test_tranche_e_paths_in_ci_targets() -> None:
    text = _TARGETS.read_text(encoding="utf-8")
    assert "packages/hermes_orchestrator/merge.py" in text
    assert "packages/hermes_orchestrator/workflow_profiles.py" in text
    assert "packages/hermes_orchestrator/_pipeline/base.py" in text
    assert "packages/hermes_orchestrator/_pipeline/_helpers.py" in text
    assert "packages/hermes_orchestrator/_pipeline/create_run.py" in text
    assert "packages/hermes_orchestrator/_pipeline/micro_slice.py" in text
    assert "packages/hermes_orchestrator/_pipeline/lifecycle_plan.py" in text
    assert "packages/hermes_orchestrator/_pipeline/critique_gates_helpers.py" in text
    assert "packages/hermes_orchestrator/_pipeline/lifecycle_start.py" in text
    assert "packages/hermes_orchestrator/_pipeline/dev_factory.py" in text
    assert "packages/hermes_orchestrator/_pipeline/__init__.py" in text

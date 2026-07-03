from __future__ import annotations

from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_PYPROJECT = _REPO / "pyproject.toml"
_TARGETS = _REPO / "scripts" / "ci" / "mypy_ci_targets.py"

_ORCHESTRATOR_STRICT = frozenset(
    {
        "orchestrator.ollama_manage",
        "orchestrator.ollama_user_policy",
        "orchestrator.preflight",
        "orchestrator.merge",
        "orchestrator.workflow_profiles",
        "orchestrator._pipeline.base",
        "orchestrator._pipeline._helpers",
        "orchestrator._pipeline.create_run",
        "orchestrator._pipeline.micro_slice",
        "orchestrator._pipeline.lifecycle_verify",
        "orchestrator._pipeline.writers",
        "orchestrator._pipeline.lifecycle_plan",
        "orchestrator._pipeline.optional_critique",
        "orchestrator._pipeline.escalation",
        "orchestrator._pipeline.critique_gates_helpers",
        "orchestrator._pipeline.critique_gates_optional_emit",
        "orchestrator._pipeline.critique_gates_stage_failed",
        "orchestrator._pipeline.critique_gates",
        "orchestrator._pipeline.lifecycle",
        "orchestrator._pipeline.lifecycle_start",
        "orchestrator._pipeline.optional_stages_research",
        "orchestrator._pipeline.optional_stages_stitch",
        "orchestrator._pipeline.optional_stages_integrator",
        "orchestrator._pipeline.optional_stages_integration",
        "orchestrator._pipeline.optional_stages_self_refinement",
        "orchestrator._pipeline.optional_stages_agent_evaluator",
        "orchestrator._pipeline.optional_stages",
        "orchestrator._pipeline.compose",
        "orchestrator._pipeline.protocol_hosts",
        "orchestrator._pipeline.pipeline_scraper",
        "orchestrator._pipeline.dev_factory",
        "orchestrator._pipeline.__init__",
    },
)

_PIPELINE_BLANKET_IGNORE = 'module = ["orchestrator._pipeline.*"]'


def test_orchestrator_strict_islands_listed() -> None:
    text = _PYPROJECT.read_text(encoding="utf-8")
    for module in _ORCHESTRATOR_STRICT:
        assert module in text, f"missing strict mypy override entry for {module}"


def test_pipeline_blanket_ignore_removed() -> None:
    text = _PYPROJECT.read_text(encoding="utf-8")
    assert _PIPELINE_BLANKET_IGNORE not in text


def test_tranche_e_paths_in_ci_targets() -> None:
    text = _TARGETS.read_text(encoding="utf-8")
    assert "packages/orchestrator/merge.py" in text
    assert "packages/orchestrator/workflow_profiles.py" in text
    assert "packages/orchestrator/_pipeline/base.py" in text
    assert "packages/orchestrator/_pipeline/_helpers.py" in text
    assert "packages/orchestrator/_pipeline/create_run.py" in text
    assert "packages/orchestrator/_pipeline/micro_slice.py" in text
    assert "packages/orchestrator/_pipeline/lifecycle_plan.py" in text
    assert "packages/orchestrator/_pipeline/critique_gates_helpers.py" in text
    assert "packages/orchestrator/_pipeline/lifecycle_start.py" in text
    assert "packages/orchestrator/_pipeline/dev_factory.py" in text
    assert "packages/orchestrator/_pipeline/__init__.py" in text

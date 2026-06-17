from __future__ import annotations

from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_PYPROJECT = _REPO / "pyproject.toml"
_TARGETS = _REPO / "scripts" / "ci" / "mypy_ci_targets.py"

_ORCHESTRATOR_STRICT = frozenset(
    {
        "nimbusware_orchestrator.ollama_manage",
        "nimbusware_orchestrator.ollama_user_policy",
        "nimbusware_orchestrator.preflight",
        "nimbusware_orchestrator.merge",
        "nimbusware_orchestrator.workflow_profiles",
        "nimbusware_orchestrator._pipeline.base",
        "nimbusware_orchestrator._pipeline._helpers",
        "nimbusware_orchestrator._pipeline.create_run",
        "nimbusware_orchestrator._pipeline.micro_slice",
        "nimbusware_orchestrator._pipeline.lifecycle_verify",
        "nimbusware_orchestrator._pipeline.writers",
        "nimbusware_orchestrator._pipeline.lifecycle_plan",
        "nimbusware_orchestrator._pipeline.optional_critique",
        "nimbusware_orchestrator._pipeline.escalation",
        "nimbusware_orchestrator._pipeline.critique_gates_helpers",
        "nimbusware_orchestrator._pipeline.critique_gates_optional_emit",
        "nimbusware_orchestrator._pipeline.critique_gates_stage_failed",
        "nimbusware_orchestrator._pipeline.critique_gates",
        "nimbusware_orchestrator._pipeline.lifecycle",
        "nimbusware_orchestrator._pipeline.lifecycle_start",
        "nimbusware_orchestrator._pipeline.optional_stages_research",
        "nimbusware_orchestrator._pipeline.optional_stages_stitch",
        "nimbusware_orchestrator._pipeline.optional_stages_integrator",
        "nimbusware_orchestrator._pipeline.optional_stages_integration",
        "nimbusware_orchestrator._pipeline.optional_stages_self_refinement",
        "nimbusware_orchestrator._pipeline.optional_stages_agent_evaluator",
        "nimbusware_orchestrator._pipeline.optional_stages",
        "nimbusware_orchestrator._pipeline.compose",
        "nimbusware_orchestrator._pipeline.protocol_hosts",
        "nimbusware_orchestrator._pipeline.pipeline_scraper",
        "nimbusware_orchestrator._pipeline.dev_factory",
        "nimbusware_orchestrator._pipeline.__init__",
    },
)

_PIPELINE_BLANKET_IGNORE = 'module = ["nimbusware_orchestrator._pipeline.*"]'


def test_orchestrator_strict_islands_listed() -> None:
    text = _PYPROJECT.read_text(encoding="utf-8")
    for module in _ORCHESTRATOR_STRICT:
        assert module in text, f"missing strict mypy override entry for {module}"


def test_pipeline_blanket_ignore_removed() -> None:
    text = _PYPROJECT.read_text(encoding="utf-8")
    assert _PIPELINE_BLANKET_IGNORE not in text


def test_tranche_e_paths_in_ci_targets() -> None:
    text = _TARGETS.read_text(encoding="utf-8")
    assert "packages/nimbusware_orchestrator/merge.py" in text
    assert "packages/nimbusware_orchestrator/workflow_profiles.py" in text
    assert "packages/nimbusware_orchestrator/_pipeline/base.py" in text
    assert "packages/nimbusware_orchestrator/_pipeline/_helpers.py" in text
    assert "packages/nimbusware_orchestrator/_pipeline/create_run.py" in text
    assert "packages/nimbusware_orchestrator/_pipeline/micro_slice.py" in text
    assert "packages/nimbusware_orchestrator/_pipeline/lifecycle_plan.py" in text
    assert "packages/nimbusware_orchestrator/_pipeline/critique_gates_helpers.py" in text
    assert "packages/nimbusware_orchestrator/_pipeline/lifecycle_start.py" in text
    assert "packages/nimbusware_orchestrator/_pipeline/dev_factory.py" in text
    assert "packages/nimbusware_orchestrator/_pipeline/__init__.py" in text

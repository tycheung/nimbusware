from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PIPE = ROOT / "packages/nimbusware_orchestrator/_pipeline"

HELPERS_IMPORT = "from nimbusware_orchestrator._pipeline._helpers import *  # noqa: F403\n\n"


def _write(path: Path, header: str, body: str, class_name: str) -> None:
    content = (
        f'"""{header}"""\n\n'
        "from __future__ import annotations\n\n"
        + HELPERS_IMPORT
        + f"class {class_name}:\n"
        + body
    )
    path.write_text(content, encoding="utf-8")


def _indent_methods(chunk: str) -> str:
    return chunk


def split_optional_stages() -> None:
    text = (PIPE / "optional_stages.py").read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)

    slices: tuple[tuple[str, str, int, int, str], ...] = (
        (
            "optional_stages_integration.py",
            "Optional integration-adapter writer stage emission.",
            9,
            38,
            "IntegrationOptionalStagesMixin",
        ),
        (
            "optional_stages_agent_evaluator.py",
            "Optional agent-evaluator stage emission.",
            39,
            202,
            "AgentEvaluatorOptionalStagesMixin",
        ),
        (
            "optional_stages_self_refinement.py",
            "Self-refinement stage marker and ungated loop.",
            203,
            472,
            "SelfRefinementOptionalStagesMixin",
        ),
        (
            "optional_stages_integrator.py",
            "Bundle integrator gate emission.",
            473,
            9999,
            "IntegratorOptionalStagesMixin",
        ),
    )

    for filename, doc, start, end, cls in slices:
        chunk = "".join(lines[start - 1 : min(end - 1, len(lines))])
        _write(PIPE / filename, doc, chunk, cls)

    facade = '''"""Integration adapter, agent evaluator, self-refinement, integrator gate."""

from __future__ import annotations

from nimbusware_orchestrator._pipeline.optional_stages_agent_evaluator import (
    AgentEvaluatorOptionalStagesMixin,
)
from nimbusware_orchestrator._pipeline.optional_stages_integrator import (
    IntegratorOptionalStagesMixin,
)
from nimbusware_orchestrator._pipeline.optional_stages_integration import (
    IntegrationOptionalStagesMixin,
)
from nimbusware_orchestrator._pipeline.optional_stages_self_refinement import (
    SelfRefinementOptionalStagesMixin,
)


class OptionalStagesMixin(
    IntegrationOptionalStagesMixin,
    AgentEvaluatorOptionalStagesMixin,
    SelfRefinementOptionalStagesMixin,
    IntegratorOptionalStagesMixin,
):
    """Composed optional pipeline stages (fo131–fo140)."""

'''
    (PIPE / "optional_stages.py").write_text(facade, encoding="utf-8")


def split_critique_gates() -> None:
    text = (PIPE / "critique_gates.py").read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)

    slices: tuple[tuple[str, str, int, int, str], ...] = (
        (
            "critique_gates_stage_failed.py",
            "Emit stage.failed on critique gate FAIL (per stage).",
            9,
            228,
            "CritiqueGateStageFailedMixin",
        ),
        (
            "critique_gates_helpers.py",
            "Critique gate helpers, findings, and hard-block checks.",
            228,
            433,
            "CritiqueGateHelpersMixin",
        ),
        (
            "critique_gates_optional_emit.py",
            "Optional universal-critique stage emitters.",
            434,
            9999,
            "CritiqueGateOptionalEmitMixin",
        ),
    )

    for filename, doc, start, end, cls in slices:
        chunk = "".join(lines[start - 1 : min(end - 1, len(lines))])
        _write(PIPE / filename, doc, chunk, cls)

    facade = '''"""Critique gate failure emitters and hard-block helpers."""

from __future__ import annotations

from nimbusware_orchestrator._pipeline.critique_gates_helpers import CritiqueGateHelpersMixin
from nimbusware_orchestrator._pipeline.critique_gates_optional_emit import (
    CritiqueGateOptionalEmitMixin,
)
from nimbusware_orchestrator._pipeline.critique_gates_stage_failed import (
    CritiqueGateStageFailedMixin,
)


class CritiqueGatesMixin(
    CritiqueGateStageFailedMixin,
    CritiqueGateHelpersMixin,
    CritiqueGateOptionalEmitMixin,
):
    """Composed critique gate mixin."""

'''
    (PIPE / "critique_gates.py").write_text(facade, encoding="utf-8")


if __name__ == "__main__":
    split_optional_stages()
    split_critique_gates()
    print("pipeline splits done")

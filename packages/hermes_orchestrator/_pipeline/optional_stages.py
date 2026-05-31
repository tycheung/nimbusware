"""Integration adapter, agent evaluator, self-refinement, integrator gate."""

from __future__ import annotations

from hermes_orchestrator._pipeline.optional_stages_agent_evaluator import (
    AgentEvaluatorOptionalStagesMixin,
)
from hermes_orchestrator._pipeline.optional_stages_integrator import (
    IntegratorOptionalStagesMixin,
)
from hermes_orchestrator._pipeline.optional_stages_integration import (
    IntegrationOptionalStagesMixin,
)
from hermes_orchestrator._pipeline.optional_stages_self_refinement import (
    SelfRefinementOptionalStagesMixin,
)


class OptionalStagesMixin(
    IntegrationOptionalStagesMixin,
    AgentEvaluatorOptionalStagesMixin,
    SelfRefinementOptionalStagesMixin,
    IntegratorOptionalStagesMixin,
):
    """Composed optional pipeline stages (fo131–fo140)."""


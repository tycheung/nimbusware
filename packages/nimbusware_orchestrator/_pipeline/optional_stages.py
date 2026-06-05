from __future__ import annotations

from nimbusware_orchestrator._pipeline.optional_stages_agent_evaluator import (
    AgentEvaluatorOptionalStagesMixin,
)
from nimbusware_orchestrator._pipeline.optional_stages_integration import (
    IntegrationOptionalStagesMixin,
)
from nimbusware_orchestrator._pipeline.optional_stages_integrator import (
    IntegratorOptionalStagesMixin,
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
    """Composed optional pipeline stages (agent evaluator, self-refinement, scraper)."""

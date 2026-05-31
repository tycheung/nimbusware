from __future__ import annotations

from hermes_orchestrator._pipeline.critique_gates_helpers import CritiqueGateHelpersMixin
from hermes_orchestrator._pipeline.critique_gates_optional_emit import (
    CritiqueGateOptionalEmitMixin,
)
from hermes_orchestrator._pipeline.critique_gates_stage_failed import (
    CritiqueGateStageFailedMixin,
)


class CritiqueGatesMixin(
    CritiqueGateStageFailedMixin,
    CritiqueGateHelpersMixin,
    CritiqueGateOptionalEmitMixin,
):
    """Composed critique gate mixin."""


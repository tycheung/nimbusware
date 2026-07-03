from __future__ import annotations

from orchestrator._pipeline.critique_gates_helpers import CritiqueGateHelpersMixin
from orchestrator._pipeline.critique_gates_optional_emit import (
    CritiqueGateOptionalEmitMixin,
)
from orchestrator._pipeline.critique_gates_stage_failed import (
    CritiqueGateStageFailedMixin,
)


class CritiqueGatesMixin(
    CritiqueGateStageFailedMixin,
    CritiqueGateHelpersMixin,
    CritiqueGateOptionalEmitMixin,
):
    pass

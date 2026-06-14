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
    pass

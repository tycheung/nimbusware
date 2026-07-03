from __future__ import annotations

from orchestrator._pipeline.lifecycle_plan import LifecyclePlanMixin
from orchestrator._pipeline.lifecycle_start import LifecycleStartMixin
from orchestrator._pipeline.lifecycle_verify import LifecycleVerifyMixin


class LifecycleMixin(LifecycleStartMixin, LifecyclePlanMixin, LifecycleVerifyMixin):
    pass

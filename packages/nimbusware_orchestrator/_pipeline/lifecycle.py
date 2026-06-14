from __future__ import annotations

from nimbusware_orchestrator._pipeline.lifecycle_plan import LifecyclePlanMixin
from nimbusware_orchestrator._pipeline.lifecycle_start import LifecycleStartMixin
from nimbusware_orchestrator._pipeline.lifecycle_verify import LifecycleVerifyMixin


class LifecycleMixin(LifecycleStartMixin, LifecyclePlanMixin, LifecycleVerifyMixin):
    pass

from __future__ import annotations

from hermes_orchestrator._pipeline.lifecycle_plan import LifecyclePlanMixin
from hermes_orchestrator._pipeline.lifecycle_start import LifecycleStartMixin
from hermes_orchestrator._pipeline.lifecycle_verify import LifecycleVerifyMixin


class LifecycleMixin(LifecycleStartMixin, LifecyclePlanMixin, LifecycleVerifyMixin):
    """Composed run lifecycle mixin (preflight → plan → verify)."""

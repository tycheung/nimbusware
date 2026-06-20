from __future__ import annotations

from nimbusware_orchestrator.llm.common import MODULE_INTEGRATOR_CRITIQUE_STAGE
from nimbusware_orchestrator.llm.post_verify_role_critique import bind_post_verify_role_critique

(
    emit_stub_module_integrator_critique_panel,
    execute_module_integrator_critique_llm,
) = bind_post_verify_role_critique(
    name="module_integrator",
    producer_tax_key="module_integrator",
    stage_name=MODULE_INTEGRATOR_CRITIQUE_STAGE,
    evidence_tag="module_integrator",
    review_label="module integrator",
)

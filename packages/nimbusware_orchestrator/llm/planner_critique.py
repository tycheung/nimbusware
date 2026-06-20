from __future__ import annotations

from nimbusware_orchestrator.llm.common import PLANNER_CRITIQUE_STAGE
from nimbusware_orchestrator.llm.post_verify_role_critique import bind_post_verify_role_critique

emit_stub_planner_critique_panel, execute_planner_critique_llm = bind_post_verify_role_critique(
    name="planner",
    producer_tax_key="planner",
    stage_name=PLANNER_CRITIQUE_STAGE,
    evidence_tag="planner",
)

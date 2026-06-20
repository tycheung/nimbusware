from __future__ import annotations

from nimbusware_orchestrator.llm.common import FRONTEND_WRITER_CRITIQUE_STAGE
from nimbusware_orchestrator.llm.post_verify_role_critique import bind_post_verify_role_critique

(
    emit_stub_frontend_writer_critique_panel,
    execute_frontend_writer_critique_llm,
) = bind_post_verify_role_critique(
    name="frontend_writer",
    producer_tax_key="frontend_writer",
    stage_name=FRONTEND_WRITER_CRITIQUE_STAGE,
    evidence_tag="frontend_writer",
    review_label="frontend writer",
)

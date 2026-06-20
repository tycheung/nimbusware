from __future__ import annotations

from nimbusware_orchestrator.llm.common import TEST_WRITER_CRITIQUE_STAGE
from nimbusware_orchestrator.llm.post_verify_role_critique import bind_post_verify_role_critique

emit_stub_test_writer_critique_panel, execute_test_writer_critique_llm = bind_post_verify_role_critique(
    name="test_writer",
    producer_tax_key="test_writer",
    stage_name=TEST_WRITER_CRITIQUE_STAGE,
    evidence_tag="test_writer",
)

from __future__ import annotations

from uuid import UUID

from nimbusware_extensions.phase2 import UniversalCritiqueRouter
from nimbusware_orchestrator.llm.common import (
    TEST_WRITER_CRITIQUE_STAGE,
    emit_stub_role_critique_panel,
    execute_post_verify_role_critique_llm,
)
from nimbusware_orchestrator.registry import RoleRegistry
from nimbusware_store.protocol import EventStore


def emit_stub_test_writer_critique_panel(
    store: EventStore,
    registry: RoleRegistry,
    critique_router: UniversalCritiqueRouter,
    *,
    run_id: UUID,
) -> None:
    emit_stub_role_critique_panel(
        store,
        registry,
        critique_router,
        run_id=run_id,
        producer_tax_key="test_writer",
        stage_name=TEST_WRITER_CRITIQUE_STAGE,
        evidence_ref="stub://test_writer",
    )


def execute_test_writer_critique_llm(
    store: EventStore,
    registry: RoleRegistry,
    critique_router: UniversalCritiqueRouter,
    *,
    run_id: UUID,
    base_url: str,
    model_id: str,
    verifier_exit_code: int,
    log_snippet: str,
    timeout_seconds: float = 120.0,
) -> bool:
    return execute_post_verify_role_critique_llm(
        store,
        registry,
        critique_router,
        run_id=run_id,
        base_url=base_url,
        model_id=model_id,
        verifier_exit_code=verifier_exit_code,
        log_snippet=log_snippet,
        producer_role="test_writer",
        stage_name=TEST_WRITER_CRITIQUE_STAGE,
        evidence_tag="test_writer",
        timeout_seconds=timeout_seconds,
    )

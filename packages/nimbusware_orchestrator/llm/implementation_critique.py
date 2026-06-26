from __future__ import annotations

from typing import cast
from uuid import UUID

from agent_core.critique_stages import IMPLEMENTATION_CRITIQUE_STAGE
from nimbusware_extensions.extension_runtime import UniversalCritiqueRouter
from nimbusware_orchestrator.llm.common import (
    emit_stub_role_critique_panel,
    execute_post_verify_role_critique_llm,
)
from nimbusware_orchestrator.registry import RoleRegistry
from nimbusware_store.protocol import EventStore


def emit_stub_implementation_critique_panel(
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
        producer_tax_key="backend_writer",
        stage_name=IMPLEMENTATION_CRITIQUE_STAGE,
        evidence_ref="stub://implementation",
    )


def execute_implementation_critique_llm(
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
    from nimbusware_config.skills_index import load_skill

    skill_body = ""
    try:
        skill_body = load_skill("refactor-rubric")
    except OSError:
        skill_body = ""
    suffix = f"Loaded skill refactor-rubric:\n{skill_body.strip()}" if skill_body.strip() else None
    meta = {"skill": "skill:refactor-rubric"} if skill_body.strip() else None
    return execute_post_verify_role_critique_llm(
        store,
        registry,
        critique_router,
        run_id=run_id,
        base_url=base_url,
        model_id=model_id,
        verifier_exit_code=verifier_exit_code,
        log_snippet=log_snippet,
        producer_role="backend_writer",
        stage_name=IMPLEMENTATION_CRITIQUE_STAGE,
        evidence_tag="implementation",
        user_suffix=suffix,
        stage_started_metadata=cast(dict[str, object], meta) if meta is not None else None,
        timeout_seconds=timeout_seconds,
    )

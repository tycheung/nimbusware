from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from nimbusware_extensions.extension_runtime import UniversalCritiqueRouter
from nimbusware_orchestrator.llm.common import (
    emit_stub_role_critique_panel,
    execute_post_verify_role_critique_llm,
)
from nimbusware_orchestrator.registry import RoleRegistry
from nimbusware_store.protocol import EventStore


def bind_post_verify_role_critique(
    *,
    name: str,
    producer_tax_key: str,
    stage_name: str,
    evidence_tag: str,
    review_label: str | None = None,
    min_pairing_count: int = 2,
    max_critics: int | None = None,
    bind_execute_llm: bool = True,
) -> tuple[
    Callable[..., None],
    Callable[..., bool] | None,
]:
    label = review_label or producer_tax_key.replace("_", " ")

    def emit_stub_panel(
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
            producer_tax_key=producer_tax_key,
            stage_name=stage_name,
            evidence_ref=f"stub://{evidence_tag}",
            min_pairing_count=min_pairing_count,
            max_critics=max_critics,
        )

    if not bind_execute_llm:
        emit_stub_panel.__name__ = f"emit_stub_{name}_critique_panel"
        return emit_stub_panel, None

    def execute_llm(
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
            producer_role=producer_tax_key,
            stage_name=stage_name,
            evidence_tag=evidence_tag,
            review_label=label,
            timeout_seconds=timeout_seconds,
        )

    emit_stub_panel.__name__ = f"emit_stub_{name}_critique_panel"
    execute_llm.__name__ = f"execute_{name}_critique_llm"
    return emit_stub_panel, execute_llm

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID

from nimbusware_env.env_flags import env_str
from nimbusware_orchestrator.workflow_scan_critique import ScanCritiqueBlock


def network_resilience_pre_emit(host: Any, block: ScanCritiqueBlock) -> bool:
    if block.backend_only and "backend_writer" not in host._critique_router.known_producer_keys():
        return False
    return True


@dataclass(frozen=True)
class ScanCritiqueEmitSpec:
    parse_block: Callable[..., ScanCritiqueBlock]
    effective: Callable[[ScanCritiqueBlock], bool]
    llm_effective: Callable[[ScanCritiqueBlock], bool]
    stage_id: str
    run_scan: Callable[[Path], dict[str, Any]]
    execute_llm: Callable[..., bool]
    emit_stub: Callable[..., None]
    pre_emit: Callable[[Any, ScanCritiqueBlock], bool] | None = None
    with_producer: bool = True


def emit_scan_critique_optional(
    host: Any,
    run_id: UUID,
    *,
    workspace: Path | None,
    workflow_profile: str | None,
    sg_snapshot: dict[str, Any] | None,
    spec: ScanCritiqueEmitSpec,
    gate_fail_for_stage: Callable[..., bool],
    ollama_runtime_from_host: Callable[..., tuple[str, float]],
) -> bool:
    block = spec.parse_block(
        host._repo_root,
        workflow_profile,
        config_materializer=host._config_materializer,
    )
    if not spec.effective(block):
        return False
    if spec.pre_emit is not None and not spec.pre_emit(host, block):
        return False
    ws = workspace or Path(env_str("NIMBUSWARE_WORKSPACE") or ".").resolve()
    scan_summary = spec.run_scan(ws)
    eff = host._effective_universal_critique_for_run(run_id)
    enforce = eff.unanimous_gate_enforce
    producer = host._security_critique_producer_for_run(sg_snapshot) if spec.with_producer else None
    emitted_llm = False
    if spec.llm_effective(block):
        model = host._selected_model_for_run(run_id)
        if model:
            base_url, timeout = ollama_runtime_from_host(host)
            emitted_llm = spec.execute_llm(
                host._store,
                host._registry,
                host._critique_router,
                run_id=run_id,
                scan_summary=scan_summary,
                base_url=base_url,
                model_id=model,
                block=block,
                timeout_seconds=timeout,
                unanimous_gate_enforce=enforce,
                **({"producer_tax_key": producer} if spec.with_producer and producer else {}),
            )
    if not emitted_llm and block.stub:
        spec.emit_stub(
            host._store,
            host._registry,
            host._critique_router,
            run_id=run_id,
            scan_summary=scan_summary,
            block=block,
            unanimous_gate_enforce=enforce,
            **({"producer_tax_key": producer} if spec.with_producer and producer else {}),
        )
    return gate_fail_for_stage(host._store.list_run_events(str(run_id)), spec.stage_id)


def emit_scan_critique_optional_for_host(
    host: Any,
    run_id: UUID,
    *,
    workspace: Path | None,
    workflow_profile: str | None,
    sg_snapshot: dict[str, Any] | None,
    spec: ScanCritiqueEmitSpec,
) -> bool:
    from nimbusware_orchestrator._pipeline._helpers import (
        gate_fail_for_stage,
        ollama_runtime_from_host,
    )

    return emit_scan_critique_optional(
        host,
        run_id,
        workspace=workspace,
        workflow_profile=workflow_profile,
        sg_snapshot=sg_snapshot,
        spec=spec,
        gate_fail_for_stage=gate_fail_for_stage,
        ollama_runtime_from_host=ollama_runtime_from_host,
    )

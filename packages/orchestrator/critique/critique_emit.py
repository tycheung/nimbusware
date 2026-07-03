from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from agent_core.models import (
    CriticVerdictEmittedEvent,
    CriticVerdictEmittedPayload,
    EventType,
    RequiredFixArtifact,
    Severity,
    StageStartedEvent,
    StageStartedPayload,
    Verdict,
)
from extensions.extension_runtime import UniversalCritiqueRouter
from orchestrator.critique.unanimous_gate import gate_decision_from_critic_verdicts
from orchestrator.llm.common import append_gate_decision_event
from orchestrator.registry import RoleRegistry
from orchestrator.workflow.scan_critique import (
    ScanCritiqueBlock,
    severity_for_critique_floor,
)
from store.protocol import EventStore


@dataclass(frozen=True)
class ScanStubCritiqueConfig:
    stage_name: str
    metadata_key: str
    specialist_tax_key: str
    evidence_scheme: str
    evidence_ok: str
    mirror_evidence: str
    min_pairing_count: int = 1
    require_specialist_in_pairing: bool = True
    metadata_scan_field: str = "scan_summary"


def emit_scan_stub_critique_panel(
    store: EventStore,
    registry: RoleRegistry,
    critique_router: UniversalCritiqueRouter,
    *,
    run_id: UUID,
    producer_tax_key: str,
    scan_summary: dict[str, Any],
    block: ScanCritiqueBlock,
    config: ScanStubCritiqueConfig,
    failed: bool,
    failing_items: list[str],
    fixes: list[RequiredFixArtifact],
    unanimous_gate_enforce: bool = False,
) -> None:
    tax_keys = critique_router.pairing_for(producer_tax_key)
    if len(tax_keys) < config.min_pairing_count:
        return
    if config.require_specialist_in_pairing and config.specialist_tax_key not in tax_keys:
        return
    owner = registry.resolve(producer_tax_key)
    severity = severity_for_critique_floor(block.severity_floor)

    store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata={
                config.metadata_key: {
                    "branch": "stub",
                    config.metadata_scan_field: scan_summary,
                },
            },
            payload=StageStartedPayload(stage_name=config.stage_name, attempt=1),
        ),
    )

    critic_payloads: list[CriticVerdictEmittedPayload] = []
    for tax_key in tax_keys:
        critic_role = registry.resolve(tax_key)
        is_specialist = tax_key == config.specialist_tax_key
        if is_specialist:
            verdict = Verdict.FAIL if failed else Verdict.PASS
            evidence = (
                [f"{config.evidence_scheme}://{item}" for item in failing_items]
                if failing_items
                else [config.evidence_ok]
            )
            in_domain = True
        else:
            verdict = Verdict.PASS if not failed else Verdict.FAIL
            evidence = [config.mirror_evidence]
            in_domain = False
        payload = CriticVerdictEmittedPayload(
            critic_role=critic_role,
            verdict=verdict,
            severity=severity if verdict == Verdict.FAIL else Severity.LOW,
            owner_role=owner,
            is_in_domain=in_domain,
            evidence_refs=evidence,
            required_fixes=fixes if verdict == Verdict.FAIL else [],
        )
        critic_payloads.append(payload)
        store.append(
            CriticVerdictEmittedEvent(
                event_type=EventType.CRITIC_VERDICT_EMITTED,
                event_id=uuid4(),
                run_id=run_id,
                occurred_at=datetime.now(timezone.utc),
                actor_role=critic_role,
                payload=payload,
            ),
        )

    gate = gate_decision_from_critic_verdicts(
        critic_payloads,
        stage_name=config.stage_name,
        unanimous_pass_required=True,
        enforce=unanimous_gate_enforce or failed,
    )
    append_gate_decision_event(store, run_id=run_id, payload=gate)

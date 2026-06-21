from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

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
from nimbusware_extensions.phase2 import UniversalCritiqueRouter
from nimbusware_orchestrator.llm.common import append_gate_decision_event
from nimbusware_orchestrator.persona_critique_llm import execute_persona_rules_critique_llm
from nimbusware_orchestrator.registry import RoleRegistry
from nimbusware_orchestrator.unanimous_gate import gate_decision_from_critic_verdicts
from nimbusware_store.protocol import EventStore

AGENT_EVALUATOR_CRITIQUE_STAGE = "agent_evaluator.critique"
_PERSONA_COVERAGE_CRITIC = "persona_coverage_critic"
_AGENT_EVALUATOR_CRITIC = "agent_evaluator_critic"

_COVERAGE_FAIL_FIX = RequiredFixArtifact.model_validate(
    {
        "artifact_schema_version": 1,
        "format": "json_patch",
        "target_files": ["configs/personas/shelves.yaml"],
        "patch_artifact": "[]",
        "validation_steps": ["assign persona slots on run.created"],
        "acceptance_criteria": "persona assignment present on run",
    },
)


class PersonaCoverageLlmResponse(BaseModel):
    model_config = {"extra": "ignore"}

    status: str = "ok"
    gaps: list[str] = Field(default_factory=list)
    summary: str = ""


def _evaluation_status(rules_eval: dict[str, Any] | None) -> str:
    if not isinstance(rules_eval, dict):
        return "gap"
    status = rules_eval.get("status")
    if isinstance(status, str) and status.strip():
        return status.strip().lower()
    return "gap"


def emit_stub_persona_coverage_critique_panel(
    store: EventStore,
    registry: RoleRegistry,
    critique_router: UniversalCritiqueRouter,
    *,
    run_id: UUID,
    rules_eval: dict[str, Any] | None,
    unanimous_gate_enforce: bool = False,
) -> None:
    tax_keys = critique_router.pairing_for("agent_evaluator")
    if len(tax_keys) < 2:
        return
    owner = registry.resolve("agent_evaluator")
    coverage_fail = _evaluation_status(rules_eval) in ("invalid", "gap")

    store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=StageStartedPayload(
                stage_name=AGENT_EVALUATOR_CRITIQUE_STAGE,
                attempt=1,
            ),
        ),
    )

    critic_payloads: list[CriticVerdictEmittedPayload] = []
    for tax_key in tax_keys:
        critic_role = registry.resolve(tax_key)
        if tax_key == _PERSONA_COVERAGE_CRITIC:
            verdict = Verdict.FAIL if coverage_fail else Verdict.PASS
            evidence = (
                ["stub://persona_coverage_gap"] if coverage_fail else ["stub://persona_coverage_ok"]
            )
            fixes = [_COVERAGE_FAIL_FIX] if verdict == Verdict.FAIL else []
        elif tax_key == _AGENT_EVALUATOR_CRITIC:
            verdict = Verdict.PASS if not coverage_fail else Verdict.FAIL
            evidence = (
                ["stub://agent_evaluator_ok"]
                if not coverage_fail
                else ["stub://agent_evaluator_gap"]
            )
            fixes = [_COVERAGE_FAIL_FIX] if verdict == Verdict.FAIL else []
        else:
            verdict = Verdict.PASS if not coverage_fail else Verdict.FAIL
            evidence = ["stub://agent_evaluator_critique"]
            fixes = [_COVERAGE_FAIL_FIX] if verdict == Verdict.FAIL else []
        payload = CriticVerdictEmittedPayload(
            critic_role=critic_role,
            verdict=verdict,
            severity=Severity.MEDIUM if verdict == Verdict.FAIL else Severity.LOW,
            owner_role=owner,
            is_in_domain=True,
            evidence_refs=evidence,
            required_fixes=fixes,
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
        stage_name=AGENT_EVALUATOR_CRITIQUE_STAGE,
        unanimous_pass_required=True,
        enforce=unanimous_gate_enforce or coverage_fail,
    )
    append_gate_decision_event(store, run_id=run_id, payload=gate)


def execute_persona_coverage_critique_llm(
    store: EventStore,
    registry: RoleRegistry,
    critique_router: UniversalCritiqueRouter,
    *,
    run_id: UUID,
    rules_eval: dict[str, Any] | None,
    base_url: str,
    model_id: str,
    timeout_seconds: float = 120.0,
    unanimous_gate_enforce: bool = False,
) -> bool:
    def _specialist_failed(
        parsed: PersonaCoverageLlmResponse, _rules: dict[str, Any] | None
    ) -> bool:
        normalized = str(parsed.status).strip().lower()
        return normalized in ("needs_work", "invalid") or bool(parsed.gaps)

    def _tax_key_failed(
        tax_key: str,
        specialist_fail: bool,
        rules: dict[str, Any] | None,
    ) -> bool:
        if tax_key == _PERSONA_COVERAGE_CRITIC:
            return specialist_fail
        return _evaluation_status(rules) in ("invalid", "gap")

    def _user_content(rules: dict[str, Any] | None) -> str:
        status = _evaluation_status(rules)
        gaps = rules.get("gaps") if isinstance(rules, dict) else []
        gap_list = [str(g).strip() for g in gaps] if isinstance(gaps, list) else []
        return f"rules_status={status!r}; rules_gaps={gap_list!r}"

    return execute_persona_rules_critique_llm(
        store,
        registry,
        critique_router,
        run_id=run_id,
        stage_name=AGENT_EVALUATOR_CRITIQUE_STAGE,
        producer_tax_key="agent_evaluator",
        specialist_tax_key=_PERSONA_COVERAGE_CRITIC,
        rules_eval=rules_eval,
        base_url=base_url,
        model_id=model_id,
        response_model=PersonaCoverageLlmResponse,
        system_prompt=(
            "You are a persona coverage critic. Return JSON only with "
            "status ok|needs_work|invalid, gaps string[], summary string."
        ),
        build_user_content=_user_content,
        specialist_failed=_specialist_failed,
        tax_key_failed=_tax_key_failed,
        build_stage_metadata=lambda parsed: {
            "agent_evaluator": {
                "persona_coverage_critique_branch": "llm",
                "llm_summary": str(parsed.summary).strip()[:500],
            },
        },
        coverage_fix=_COVERAGE_FAIL_FIX,
        evidence_prefix="llm://persona_coverage",
        timeout_seconds=timeout_seconds,
        unanimous_gate_enforce=unanimous_gate_enforce,
    )
